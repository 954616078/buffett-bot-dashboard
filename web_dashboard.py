"""Web dashboard for Trend_OB_AI paper trading."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, redirect, render_template, request, session, url_for

from ai_reminder import send_to_telegram
from config import DB_PATH, PAPER_INITIAL_CASH, TELEGRAM_TARGET
from database import init_db
from paper_trader import PaperTrader
from portfolio_analytics import compute_fund_metrics
from runtime_settings import get_setting, get_settings, init_runtime_settings, set_setting
from seed_loader import seed_if_empty

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__, template_folder=str(BASE_DIR / "templates"), static_folder=str(BASE_DIR / "static"))
app.secret_key = os.getenv("DASHBOARD_SECRET_KEY", "please-change-dashboard-secret")

DASHBOARD_AUTH_ENABLED = os.getenv("DASHBOARD_AUTH_ENABLED", "1") == "1"
DASHBOARD_USERNAME = os.getenv("DASHBOARD_USERNAME", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "ChangeMe123!")

SETTINGS_SCHEMA: dict[str, dict[str, Any]] = {
    "ma_short": {"default": 20, "type": "int", "label": "短均线 MA"},
    "ma_long": {"default": 60, "type": "int", "label": "长均线 MA"},
    "max_alerts_per_run": {"default": 30, "type": "int", "label": "单次最多提醒"},
    "alert_require_alignment": {"default": True, "type": "bool", "label": "必须趋势与OB共振"},
    "paper_base_risk_pct": {"default": 0.005, "type": "float", "label": "基础风险比例"},
    "paper_min_risk_pct": {"default": 0.003, "type": "float", "label": "最小风险比例"},
    "paper_max_risk_pct": {"default": 0.01, "type": "float", "label": "最大风险比例"},
    "paper_max_position_pct": {"default": 0.05, "type": "float", "label": "单票最大仓位"},
    "paper_max_positions": {"default": 5, "type": "int", "label": "最大持仓数"},
    "paper_stop_loss_pct": {"default": 0.015, "type": "float", "label": "止损比例"},
    "paper_take_profit_pct": {"default": 0.06, "type": "float", "label": "止盈比例"},
    "paper_learn_lookback": {"default": 20, "type": "int", "label": "风险学习回看"},
    "max_hold_days": {"default": 5, "type": "int", "label": "最大持有天数"},
    "daily_loss_limit_pct": {"default": 0.03, "type": "float", "label": "单日亏损熔断比例"},
    "max_drawdown_limit_pct": {"default": 0.12, "type": "float", "label": "最大回撤熔断比例"},
    "enable_circuit_breaker": {"default": True, "type": "bool", "label": "启用组合熔断"},
    "telegram_target": {"default": TELEGRAM_TARGET, "type": "str", "label": "Telegram 目标"},
}

_task_lock = threading.Lock()
_task_state: dict[str, Any] = {
    "running": False,
    "name": "",
    "started_at": "",
    "finished_at": "",
    "return_code": None,
    "output_tail": "",
}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _safe_fetchone(query: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
    try:
        with _connect() as conn:
            return conn.execute(query, params).fetchone()
    except sqlite3.Error:
        return None


def _safe_fetchall(query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    try:
        with _connect() as conn:
            return conn.execute(query, params).fetchall()
    except sqlite3.Error:
        return []


def _cast_setting(value: Any, setting_type: str) -> Any:
    if setting_type == "int":
        return int(value)
    if setting_type == "float":
        return float(value)
    if setting_type == "bool":
        return str(value).lower() in {"1", "true", "yes", "on"}
    return str(value)


def _load_settings_payload() -> list[dict[str, Any]]:
    defaults = {key: meta["default"] for key, meta in SETTINGS_SCHEMA.items()}
    values = get_settings(defaults)
    payload = []
    for key, meta in SETTINGS_SCHEMA.items():
        payload.append({"key": key, "label": meta["label"], "type": meta["type"], "value": values[key]})
    return payload


def _compute_summary() -> dict[str, Any]:
    account = _safe_fetchone("SELECT cash, equity, risk_pct, updated_at FROM paper_account WHERE id=1")
    if account is None:
        cash = PAPER_INITIAL_CASH
        equity = PAPER_INITIAL_CASH
        risk_pct = 0.0
        account_updated_at = ""
    else:
        cash = float(account["cash"])
        equity = float(account["equity"])
        risk_pct = float(account["risk_pct"])
        account_updated_at = str(account["updated_at"])

    total_return_pct = ((equity - PAPER_INITIAL_CASH) / PAPER_INITIAL_CASH) * 100 if PAPER_INITIAL_CASH else 0.0
    today = datetime.now().strftime("%Y-%m-%d")
    today_scans = _safe_fetchone("SELECT COUNT(*) AS n FROM trades WHERE date LIKE ?", (f"{today}%",))
    today_signals = _safe_fetchone(
        """
        SELECT COUNT(*) AS n FROM trades
        WHERE date LIKE ?
        AND (
            (trend='UPTREND' AND ob_signal='BUY_PRESSURE')
            OR
            (trend='DOWNTREND' AND ob_signal='SELL_PRESSURE')
        )
        """,
        (f"{today}%",),
    )
    open_positions = _safe_fetchone("SELECT COUNT(*) AS n FROM paper_positions")
    pnl_today = _safe_fetchone("SELECT COALESCE(SUM(realized_pnl),0) AS v FROM paper_orders WHERE ts LIKE ?", (f"{today}%",))
    return {
        "cash": cash,
        "equity": equity,
        "risk_pct": risk_pct,
        "total_return_pct": total_return_pct,
        "today_scans": int(today_scans["n"]) if today_scans else 0,
        "today_signals": int(today_signals["n"]) if today_signals else 0,
        "open_positions": int(open_positions["n"]) if open_positions else 0,
        "realized_pnl_today": float(pnl_today["v"]) if pnl_today else 0.0,
        "account_updated_at": account_updated_at,
    }


def _compute_equity_curve(limit: int = 60) -> list[dict[str, Any]]:
    rows = _safe_fetchall(
        """
        SELECT ts, equity_after
        FROM paper_orders
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )
    if not rows:
        return [{"ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "equity": PAPER_INITIAL_CASH}]
    points = [{"ts": str(row["ts"]), "equity": float(row["equity_after"])} for row in rows]
    points.reverse()
    return points


def _list_positions() -> list[dict[str, Any]]:
    rows = _safe_fetchall(
        """
        SELECT p.symbol, p.qty, p.avg_cost, p.updated_at, t.last_price
        FROM paper_positions p
        LEFT JOIN (
            SELECT t1.stock, t1.last_price
            FROM trades t1
            JOIN (
                SELECT stock, MAX(id) AS max_id FROM trades GROUP BY stock
            ) t2 ON t1.stock=t2.stock AND t1.id=t2.max_id
        ) t ON t.stock=p.symbol
        ORDER BY p.symbol
        """
    )
    result: list[dict[str, Any]] = []
    for row in rows:
        qty = int(row["qty"])
        avg_cost = float(row["avg_cost"])
        last_price = float(row["last_price"]) if row["last_price"] is not None else 0.0
        unrealized = (last_price - avg_cost) * qty if last_price > 0 else 0.0
        unrealized_pct = ((last_price - avg_cost) / avg_cost) * 100 if last_price > 0 and avg_cost > 0 else 0.0
        result.append(
            {
                "symbol": str(row["symbol"]),
                "qty": qty,
                "avg_cost": avg_cost,
                "last_price": last_price,
                "unrealized": unrealized,
                "unrealized_pct": unrealized_pct,
                "updated_at": str(row["updated_at"]),
            }
        )
    return result


def _list_latest_signals(limit: int = 40) -> list[dict[str, Any]]:
    rows = _safe_fetchall(
        """
        SELECT date, stock, last_price, trend, ob_signal, ai_analysis
        FROM trades
        WHERE
            (trend='UPTREND' AND ob_signal='BUY_PRESSURE')
            OR
            (trend='DOWNTREND' AND ob_signal='SELL_PRESSURE')
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )
    return [
        {
            "date": str(row["date"]),
            "stock": str(row["stock"]),
            "last_price": float(row["last_price"]) if row["last_price"] is not None else 0.0,
            "trend": str(row["trend"]),
            "ob_signal": str(row["ob_signal"]),
            "ai_analysis": str(row["ai_analysis"]),
        }
        for row in rows
    ]


def _list_orders(limit: int = 80) -> list[dict[str, Any]]:
    rows = _safe_fetchall(
        """
        SELECT ts, symbol, action, qty, price, reason, realized_pnl, equity_after
        FROM paper_orders
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )
    return [
        {
            "ts": str(row["ts"]),
            "symbol": str(row["symbol"]),
            "action": str(row["action"]),
            "qty": int(row["qty"]),
            "price": float(row["price"]),
            "reason": str(row["reason"]),
            "realized_pnl": float(row["realized_pnl"]),
            "equity_after": float(row["equity_after"]),
        }
        for row in rows
    ]


def _build_daily_ai_comment() -> dict[str, Any]:
    today = datetime.now().strftime("%Y-%m-%d")
    summary = _compute_summary()
    latest_signal = _safe_fetchone(
        """
        SELECT stock, trend, ob_signal, ai_analysis
        FROM trades
        WHERE date LIKE ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (f"{today}%",),
    )
    recent_orders = _safe_fetchall(
        """
        SELECT action, symbol, realized_pnl
        FROM paper_orders
        WHERE ts LIKE ?
        ORDER BY id DESC
        LIMIT 5
        """,
        (f"{today}%",),
    )

    mood = "中性"
    if summary["realized_pnl_today"] > 100:
        mood = "偏强"
    elif summary["realized_pnl_today"] < -100:
        mood = "偏弱"

    lines = [
        f"今日账户表现{mood}，当前权益 ${summary['equity']:.2f}，当日已实现盈亏 ${summary['realized_pnl_today']:.2f}。",
        f"今日扫描 {summary['today_scans']} 只，出现有效信号 {summary['today_signals']} 条，当前持仓 {summary['open_positions']} 只。",
    ]

    if latest_signal:
        direction = "做多" if latest_signal["trend"] == "UPTREND" else "做空/减仓"
        lines.append(f"最近信号：{latest_signal['stock']}，方向偏向{direction}。")
        ai_text = str(latest_signal["ai_analysis"] or "").strip()
        if ai_text and ai_text != "NO_ACTIONABLE_SIGNAL":
            lines.append(f"AI 提示：{ai_text[:120]}")

    if recent_orders:
        trade_text = "，".join([f"{row['action']} {row['symbol']}" for row in recent_orders[:3]])
        lines.append(f"最近执行：{trade_text}。")

    lines.append("建议：继续执行纪律止损，优先保留趋势与OB共振的标的。")
    return {"date": today, "comment": "\n".join(lines)}


def _build_telegram_summary() -> str:
    summary = _compute_summary()
    signals = _list_latest_signals(limit=5)
    lines = [
        "📊 Buffett模式输出",
        "",
        f"账户权益: {summary['equity']:.2f}",
        f"今日扫描: {summary['today_scans']}",
        f"今日有效信号: {summary['today_signals']}",
        "",
        "有效信号:",
    ]
    if not signals:
        lines.append("- 暂无")
    else:
        for s in signals:
            direction = "买入" if s["trend"] == "UPTREND" else "卖出/做空"
            lines.append(f"- {s['stock']} {s['last_price']:.2f} {direction}")
    lines.extend(["", "风险提示: 请严格执行止损规则"])
    return "\n".join(lines)


def _run_task(task_name: str, command: list[str]) -> None:
    with _task_lock:
        if _task_state["running"]:
            return
        _task_state.update(
            {
                "running": True,
                "name": task_name,
                "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "finished_at": "",
                "return_code": None,
                "output_tail": "",
            }
        )

    def worker() -> None:
        try:
            proc = subprocess.run(command, cwd=str(BASE_DIR), capture_output=True, text=True, timeout=1200, check=False)
            output = (proc.stdout or "") + "\n" + (proc.stderr or "")
            tail = "\n".join([line for line in output.splitlines() if line.strip()][-40:])
            with _task_lock:
                _task_state["return_code"] = proc.returncode
                _task_state["output_tail"] = tail
        except Exception as exc:  # pragma: no cover
            with _task_lock:
                _task_state["return_code"] = -1
                _task_state["output_tail"] = f"任务失败: {exc}"
        finally:
            with _task_lock:
                _task_state["running"] = False
                _task_state["finished_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()


@app.before_request
def require_auth() -> Any:
    if not DASHBOARD_AUTH_ENABLED:
        return None
    endpoint = request.endpoint or ""
    if endpoint.startswith("static"):
        return None
    if endpoint in {"login_page", "login_action"}:
        return None
    if session.get("authenticated"):
        return None
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "message": "未登录"}), 401
    return redirect(url_for("login_page"))


@app.route("/login")
def login_page() -> str:
    return render_template("login.html")


@app.post("/login")
def login_action() -> Any:
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    if username == DASHBOARD_USERNAME and password == DASHBOARD_PASSWORD:
        session["authenticated"] = True
        return redirect(url_for("index"))
    return render_template("login.html", error="账号或密码错误")


@app.post("/logout")
def logout() -> Any:
    session.clear()
    return redirect(url_for("login_page"))


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.get("/api/summary")
def api_summary() -> Any:
    return jsonify(_compute_summary())


@app.get("/api/equity")
def api_equity() -> Any:
    return jsonify(_compute_equity_curve())


@app.get("/api/positions")
def api_positions() -> Any:
    return jsonify(_list_positions())


@app.get("/api/signals")
def api_signals() -> Any:
    return jsonify(_list_latest_signals())


@app.get("/api/orders")
def api_orders() -> Any:
    return jsonify(_list_orders())


@app.get("/api/settings")
def api_settings() -> Any:
    return jsonify(_load_settings_payload())


@app.post("/api/settings")
def api_settings_update() -> Any:
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "message": "参数格式错误"}), 400
    for key, value in payload.items():
        meta = SETTINGS_SCHEMA.get(key)
        if not meta:
            continue
        cast_value = _cast_setting(value, meta["type"])
        set_setting(key, cast_value)
    return jsonify({"ok": True, "message": "参数已保存"})


@app.get("/api/task")
def api_task() -> Any:
    with _task_lock:
        return jsonify(dict(_task_state))


@app.get("/api/daily-comment")
def api_daily_comment() -> Any:
    return jsonify(_build_daily_ai_comment())


@app.get("/api/fund-metrics")
def api_fund_metrics() -> Any:
    with _connect() as conn:
        summary = _compute_summary()
        return jsonify(compute_fund_metrics(conn, float(summary["equity"])))


@app.post("/api/run/scan")
def api_run_scan() -> Any:
    with _task_lock:
        if _task_state["running"]:
            return jsonify({"ok": False, "message": "已有任务在运行"}), 409
    _run_task("scan", ["python", "run_system.py"])
    return jsonify({"ok": True, "message": "扫描任务已启动"})


@app.post("/api/run/review")
def api_run_review() -> Any:
    with _task_lock:
        if _task_state["running"]:
            return jsonify({"ok": False, "message": "已有任务在运行"}), 409
    _run_task("review", ["python", "daily_review.py"])
    return jsonify({"ok": True, "message": "复盘任务已启动"})


@app.post("/api/run/telegram")
def api_run_telegram() -> Any:
    target = str(get_setting("telegram_target", TELEGRAM_TARGET)).strip()
    if not target:
        return jsonify({"ok": False, "message": "Telegram 目标为空"}), 400
    sent = send_to_telegram(_build_telegram_summary(), target=target)
    if not sent:
        return jsonify({"ok": False, "message": "Telegram 推送失败"}), 500
    return jsonify({"ok": True, "message": f"已推送到 {target}"})


def _bootstrap_storage() -> None:
    init_db()
    init_runtime_settings()
    # Ensure paper trading tables exist before optional seeding.
    PaperTrader()
    seed_if_empty(DB_PATH, str(BASE_DIR / "seed_data.json"))


_bootstrap_storage()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
