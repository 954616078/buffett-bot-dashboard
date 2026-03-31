"""Main entrypoint for Trend + OB + OpenClaw scanner."""

from __future__ import annotations

from typing import List

from ai_reminder import openclaw_reminder, send_to_telegram
from config import (
    ALERT_ONLY_WHEN_SIGNAL,
    ALERT_REQUIRE_ALIGNMENT,
    LONGPORT_KLINE_COUNT,
    MA_LONG,
    MA_SHORT,
    MAX_ALERTS_PER_RUN,
    STOCK_LIST,
    TOP_MARKETCAP_COUNT,
    PAPER_TRADING_ENABLED,
    USE_LONGPORT,
    USE_TOP_MARKETCAP_UNIVERSE,
)
from data_fetch import (
    BrowserDataClient,
    parse_kline_html,
    parse_orderbook_html,
)
from database import init_db, save_trade
from ob_analysis import analyze_orderbook
from trend_analysis import analyze_trend
from paper_trader import PaperTrader
from runtime_settings import get_settings, init_runtime_settings

try:
    from longport_data import LongPortDataClient
except Exception:  # pragma: no cover
    LongPortDataClient = None  # type: ignore


def build_summary(lines: List[str]) -> str:
    header = "趋势+OB 扫描结果"
    return header + "\n\n" + "\n".join(lines)


def is_actionable_signal(trend_signal: str, ob_signal: str) -> bool:
    if ALERT_REQUIRE_ALIGNMENT:
        return (trend_signal == "UPTREND" and ob_signal == "BUY_PRESSURE") or (
            trend_signal == "DOWNTREND" and ob_signal == "SELL_PRESSURE"
        )
    return trend_signal in {"UPTREND", "DOWNTREND"} and ob_signal in {
        "BUY_PRESSURE",
        "SELL_PRESSURE",
    }


def main() -> None:
    init_db()
    init_runtime_settings()
    settings = get_settings(
        {
            "ma_short": MA_SHORT,
            "ma_long": MA_LONG,
            "max_alerts_per_run": MAX_ALERTS_PER_RUN,
            "alert_require_alignment": ALERT_REQUIRE_ALIGNMENT,
        }
    )
    ma_short = int(settings["ma_short"])
    ma_long = int(settings["ma_long"])
    max_alerts_per_run = int(settings["max_alerts_per_run"])
    alert_require_alignment = bool(settings["alert_require_alignment"])
    summary_lines: List[str] = []
    alert_lines: List[str] = []
    paper_trade_lines: List[str] = []
    scan_errors = 0
    longport_client = None
    paper_trader = PaperTrader() if PAPER_TRADING_ENABLED else None

    if USE_LONGPORT and LongPortDataClient is not None:
        try:
            longport_client = LongPortDataClient()
            print("已启用 LongPort API 数据源")
        except Exception as exc:
            print(f"LongPort 初始化失败，回退网页抓取: {exc}")

    with BrowserDataClient() as client:
        universe = STOCK_LIST
        if USE_TOP_MARKETCAP_UNIVERSE:
            try:
                fetched = client.fetch_top_us_market_cap_tickers(limit=TOP_MARKETCAP_COUNT)
                if fetched:
                    universe = fetched
                    print(f"已加载美股市值前{len(universe)}股票进行监控")
                else:
                    print("动态股票池为空，回退到配置股票列表")
            except Exception as exc:
                print(f"动态股票池加载失败，回退到配置股票列表: {exc}")

        for stock in universe:
            print(f"扫描 {stock} ...")

            try:
                if longport_client is not None:
                    df = longport_client.fetch_kline_df(stock, count=LONGPORT_KLINE_COUNT)
                    ob_data = longport_client.fetch_orderbook(stock)
                    if df.empty:
                        raise RuntimeError("LongPort returned empty candlesticks")
                    # For some quote plans (e.g., Nasdaq Basic), depth may be unavailable.
                    # Fall back to Yahoo top-level bid/ask so OB signal still works.
                    if not ob_data.get("bids") and not ob_data.get("asks"):
                        try:
                            ob_html = client.fetch_orderbook_html(stock)
                            ob_data = parse_orderbook_html(ob_html)
                        except Exception:
                            ob_data = {"bids": [], "asks": []}
                else:
                    kline_html = client.fetch_kline_html(stock)
                    ob_html = client.fetch_orderbook_html(stock)
                    df = parse_kline_html(kline_html)
                    ob_data = parse_orderbook_html(ob_html)
            except Exception as exc:
                err = f"{stock}: 数据抓取失败 - {exc}"
                print(err)
                summary_lines.append(err)
                scan_errors += 1
                continue

            trend_signal = analyze_trend(df, ma_short=ma_short, ma_long=ma_long)
            ob_signal = analyze_orderbook(ob_data)
            last_price = float(df.iloc[-1]["Close"])

            if alert_require_alignment:
                actionable = (trend_signal == "UPTREND" and ob_signal == "BUY_PRESSURE") or (
                    trend_signal == "DOWNTREND" and ob_signal == "SELL_PRESSURE"
                )
            else:
                actionable = trend_signal in {"UPTREND", "DOWNTREND"} and ob_signal in {
                    "BUY_PRESSURE",
                    "SELL_PRESSURE",
                }
            if actionable:
                ai_result = openclaw_reminder(stock, trend_signal, ob_signal, last_price)
                alert_lines.append(
                    f"{stock}: close={last_price:.2f}, trend={trend_signal}, ob={ob_signal}"
                )
                print(f"[SIGNAL] {stock} => {trend_signal} + {ob_signal}")
            else:
                ai_result = "NO_ACTIONABLE_SIGNAL"

            save_trade(stock, last_price, trend_signal, ob_signal, ai_result)

            if paper_trader is not None:
                action = paper_trader.on_signal(stock, last_price, trend_signal, ob_signal)
                if action is not None:
                    line = (
                        f"{action.action} {action.symbol} x{action.qty} @ {action.price:.2f} "
                        f"[{action.reason}] pnl={action.realized_pnl:.2f}"
                    )
                    paper_trade_lines.append(line)
                    print(f"[PAPER] {line}")

            summary_lines.append(
                f"{stock}: close={last_price:.2f}, trend={trend_signal}, ob={ob_signal}"
            )

    if not summary_lines:
        print("无可用扫描结果")
        return

    if ALERT_ONLY_WHEN_SIGNAL:
        if not alert_lines:
            if paper_trade_lines and paper_trader is not None:
                snap = paper_trader.snapshot()
                summary = build_summary(
                    [
                        f"扫描总数: {len(summary_lines)}",
                        f"有效信号: {len(alert_lines)}",
                        f"抓取错误: {scan_errors}",
                        "模拟交易执行:",
                        *paper_trade_lines[:max_alerts_per_run],
                        f"账户: cash={snap['cash']:.2f}, equity={snap['equity']:.2f}, risk={snap['risk_pct']:.4f}",
                        (
                            f"风控: 熔断触发 {','.join(snap['risk_state']['triggered_reasons'])}"
                            if snap.get("risk_state", {}).get("triggered_reasons")
                            else "风控: 正常"
                        ),
                    ]
                )
                send_to_telegram(summary)
            print("本轮无有效信号，不发送TG提醒")
            return
        alerts = alert_lines[:max_alerts_per_run]
        blocks = [
            f"扫描总数: {len(summary_lines)}",
            f"有效信号: {len(alert_lines)}",
            f"抓取错误: {scan_errors}",
            "---",
            *alerts,
        ]
        if paper_trader is not None:
            snap = paper_trader.snapshot()
            blocks.extend(
                [
                    "---",
                    "模拟交易:",
                    *(paper_trade_lines[:max_alerts_per_run] if paper_trade_lines else ["本轮无下单"]),
                    f"账户: cash={snap['cash']:.2f}, equity={snap['equity']:.2f}, risk={snap['risk_pct']:.4f}",
                    (
                        f"风控: 熔断触发 {','.join(snap['risk_state']['triggered_reasons'])}"
                        if snap.get("risk_state", {}).get("triggered_reasons")
                        else "风控: 正常"
                    ),
                ]
            )
        summary = build_summary(blocks)
    else:
        summary = build_summary(summary_lines)

    pushed = send_to_telegram(summary)
    if pushed:
        print("已发送 Telegram 信号提醒")
    else:
        print("未发送 Telegram（请检查 TELEGRAM_TARGET）")


if __name__ == "__main__":
    main()
