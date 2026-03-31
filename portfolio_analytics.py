"""Portfolio-level analytics and risk gating helpers."""

from __future__ import annotations

import math
import sqlite3
from statistics import mean, pstdev
from typing import Any

from config import PAPER_INITIAL_CASH
from runtime_settings import get_settings, init_runtime_settings


def _safe_div(num: float, den: float) -> float:
    if den == 0:
        return 0.0
    return num / den


def _load_rows(conn: sqlite3.Connection, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    return conn.execute(query, params).fetchall()


def get_risk_status(conn: sqlite3.Connection, equity: float) -> dict[str, Any]:
    """Return portfolio-level circuit-breaker status."""
    init_runtime_settings()
    settings = get_settings(
        {
            "daily_loss_limit_pct": 0.03,
            "max_drawdown_limit_pct": 0.12,
            "enable_circuit_breaker": True,
        }
    )
    daily_loss_limit_pct = float(settings["daily_loss_limit_pct"])
    max_drawdown_limit_pct = float(settings["max_drawdown_limit_pct"])
    enable_circuit_breaker = bool(settings["enable_circuit_breaker"])

    today_pnl_row = conn.execute(
        "SELECT COALESCE(SUM(realized_pnl),0) AS v FROM paper_orders WHERE ts LIKE date('now','localtime') || '%'"
    ).fetchone()
    today_realized_pnl = float(today_pnl_row[0] if today_pnl_row else 0.0)
    daily_loss_limit = PAPER_INITIAL_CASH * daily_loss_limit_pct
    daily_loss_pct = _safe_div(-today_realized_pnl, PAPER_INITIAL_CASH)

    peak_row = conn.execute("SELECT MAX(equity_after) FROM paper_orders").fetchone()
    peak_equity = float(peak_row[0]) if peak_row and peak_row[0] is not None else max(PAPER_INITIAL_CASH, equity)
    peak_equity = max(peak_equity, PAPER_INITIAL_CASH, 1.0)
    drawdown_pct = max(0.0, (peak_equity - equity) / peak_equity)

    triggered_reasons: list[str] = []
    if enable_circuit_breaker:
        if today_realized_pnl <= -daily_loss_limit:
            triggered_reasons.append("DAILY_LOSS_LIMIT")
        if drawdown_pct >= max_drawdown_limit_pct:
            triggered_reasons.append("MAX_DRAWDOWN_LIMIT")

    return {
        "enabled": enable_circuit_breaker,
        "can_open_new_positions": len(triggered_reasons) == 0,
        "triggered_reasons": triggered_reasons,
        "today_realized_pnl": today_realized_pnl,
        "daily_loss_limit": daily_loss_limit,
        "daily_loss_pct": daily_loss_pct,
        "drawdown_pct": drawdown_pct,
        "max_drawdown_limit_pct": max_drawdown_limit_pct,
        "peak_equity": peak_equity,
    }


def compute_fund_metrics(conn: sqlite3.Connection, current_equity: float) -> dict[str, Any]:
    """Compute simple fund-style performance KPIs."""
    conn.row_factory = sqlite3.Row

    sells = _load_rows(conn, "SELECT realized_pnl FROM paper_orders WHERE action='SELL'")
    total_closed = len(sells)
    wins = [float(r["realized_pnl"]) for r in sells if float(r["realized_pnl"]) > 0]
    losses = [float(r["realized_pnl"]) for r in sells if float(r["realized_pnl"]) < 0]
    win_rate = _safe_div(len(wins), total_closed)
    avg_win = mean(wins) if wins else 0.0
    avg_loss = mean(losses) if losses else 0.0
    gross_profit = sum(wins)
    gross_loss_abs = abs(sum(losses))
    profit_factor = _safe_div(gross_profit, gross_loss_abs) if gross_loss_abs > 0 else (999.0 if gross_profit > 0 else 0.0)

    rows = _load_rows(conn, "SELECT equity_after FROM paper_orders ORDER BY id")
    equity_series = [PAPER_INITIAL_CASH] + [float(r["equity_after"]) for r in rows]
    peak = PAPER_INITIAL_CASH
    max_drawdown = 0.0
    for e in equity_series:
        peak = max(peak, e)
        dd = (peak - e) / peak if peak > 0 else 0.0
        max_drawdown = max(max_drawdown, dd)

    # End-of-day equity for simple daily return Sharpe approximation.
    eod_rows = _load_rows(
        conn,
        """
        SELECT substr(ts,1,10) AS d, MAX(id) AS max_id
        FROM paper_orders
        GROUP BY substr(ts,1,10)
        ORDER BY d
        """,
    )
    eod_equity: list[float] = []
    for r in eod_rows:
        one = conn.execute("SELECT equity_after FROM paper_orders WHERE id=?", (int(r["max_id"]),)).fetchone()
        if one and one[0] is not None:
            eod_equity.append(float(one[0]))

    daily_returns: list[float] = []
    prev = PAPER_INITIAL_CASH
    for eod in eod_equity:
        if prev > 0:
            daily_returns.append((eod - prev) / prev)
        prev = eod
    sharpe = 0.0
    if len(daily_returns) >= 2:
        mu = mean(daily_returns)
        sigma = pstdev(daily_returns)
        if sigma > 1e-9:
            sharpe = (mu / sigma) * math.sqrt(252)

    turnover_row = conn.execute("SELECT COALESCE(SUM(notional),0) FROM paper_orders").fetchone()
    turnover = _safe_div(float(turnover_row[0] if turnover_row else 0.0), PAPER_INITIAL_CASH)

    risk = get_risk_status(conn, current_equity)

    return {
        "closed_trades": total_closed,
        "win_rate_pct": win_rate * 100,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": profit_factor,
        "max_drawdown_pct": max_drawdown * 100,
        "sharpe": sharpe,
        "turnover_x": turnover,
        "risk": risk,
    }
