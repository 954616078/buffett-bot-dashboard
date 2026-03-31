"""OpenClaw integration for natural-language trade reminders."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Optional

from config import OPENCLAW_TIMEOUT_SECONDS, TELEGRAM_TARGET


def _resolve_openclaw_cmd() -> str:
    for name in ("openclaw-cn", "openclaw"):
        resolved = shutil.which(name)
        if resolved:
            return resolved
    npm_global_cmd = os.path.expandvars(r"%APPDATA%\npm\openclaw-cn.cmd")
    if os.path.exists(npm_global_cmd):
        return npm_global_cmd
    return "openclaw-cn"


def build_prompt(stock: str, trend_signal: str, ob_signal: str, last_price: float) -> str:
    return f"""
你是一名趋势交易专家，请严格基于以下输入直接输出结论。

硬性要求：
- 不要向用户索要任何额外信息（不要说“请提供股票代码/指标/截图”）。
- 不要要求 TradingView 截图。
- 只允许使用我给你的4个输入字段。
- 如果信号不足，也必须给“观望”结论和风险提示。

股票: {stock}
最新价格: {last_price:.2f}
趋势信号: {trend_signal}
OB信号: {ob_signal}

请输出：
1) 是否存在趋势交易机会（是/否）
2) 建议入场价格
3) 建议止损位置
4) 建议止盈目标
5) 风险提示（最多2条）
""".strip()


def _fallback_brief(stock: str, trend_signal: str, ob_signal: str, last_price: float) -> str:
    action = "观望"
    if trend_signal == "UPTREND" and ob_signal == "BUY_PRESSURE":
        action = "可关注顺势做多"
    elif trend_signal == "DOWNTREND" and ob_signal == "SELL_PRESSURE":
        action = "可关注顺势做空或回避做多"
    return (
        f"股票: {stock}\n"
        f"结论: {action}\n"
        f"入场参考: {last_price:.2f} 附近分批\n"
        f"止损参考: 偏离入场约 1.5%-2.0%\n"
        f"止盈参考: 先看 2R，再看 3R\n"
        f"风险提示: 当前信号为 trend={trend_signal}, ob={ob_signal}，若后续信号背离则应降低仓位。"
    )


def openclaw_reminder(stock: str, trend_signal: str, ob_signal: str, last_price: float) -> str:
    prompt = build_prompt(stock, trend_signal, ob_signal, last_price)
    openclaw_cmd = _resolve_openclaw_cmd()
    cmd = [
        openclaw_cmd,
        "agent",
        "--local",
        "--agent",
        "main",
        "--json",
        "--message",
        prompt,
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=OPENCLAW_TIMEOUT_SECONDS,
            check=False,
        )
    except Exception as exc:
        return f"OpenClaw调用失败: {exc}"

    if proc.returncode != 0:
        return f"OpenClaw调用失败: {proc.stderr.strip() or proc.stdout.strip()}"

    # openclaw --json output may still include wrapper lines; try best-effort parse.
    stdout = (proc.stdout or "").strip()
    try:
        payload = json.loads(stdout)
        if isinstance(payload, dict):
            payloads = payload.get("payloads")
            if isinstance(payloads, list) and payloads:
                first = payloads[0]
                if isinstance(first, dict) and isinstance(first.get("text"), str):
                    text = first["text"].strip()
                    if ("请提供" in text) or ("截图" in text) or ("TradingView" in text):
                        return _fallback_brief(stock, trend_signal, ob_signal, last_price)
                    return text
        for key in ("text", "message", "output", "result"):
            if key in payload and isinstance(payload[key], str):
                text = payload[key].strip()
                if ("请提供" in text) or ("截图" in text) or ("TradingView" in text):
                    return _fallback_brief(stock, trend_signal, ob_signal, last_price)
                return text
        return stdout
    except json.JSONDecodeError:
        if ("请提供" in stdout) or ("截图" in stdout) or ("TradingView" in stdout):
            return _fallback_brief(stock, trend_signal, ob_signal, last_price)
        return stdout


def send_to_telegram(message: str, target: Optional[str] = None) -> bool:
    chat_target = target or TELEGRAM_TARGET
    if not chat_target:
        return False

    openclaw_cmd = _resolve_openclaw_cmd()
    cmd = [
        openclaw_cmd,
        "message",
        "send",
        "--channel",
        "telegram",
        "--target",
        chat_target,
        "--message",
        message,
    ]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False
    )
    return proc.returncode == 0
