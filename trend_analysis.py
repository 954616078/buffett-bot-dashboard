"""Trend signal based on moving-average alignment."""

from __future__ import annotations

import pandas as pd


def analyze_trend(df: pd.DataFrame, ma_short: int = 20, ma_long: int = 60) -> str:
    if len(df) < ma_long:
        return "NO_TREND"

    frame = df.copy()
    frame[f"MA{ma_short}"] = frame["Close"].rolling(ma_short).mean()
    frame[f"MA{ma_long}"] = frame["Close"].rolling(ma_long).mean()

    latest = frame.iloc[-1]
    if latest["Close"] > latest[f"MA{ma_short}"] > latest[f"MA{ma_long}"]:
        return "UPTREND"
    if latest["Close"] < latest[f"MA{ma_short}"] < latest[f"MA{ma_long}"]:
        return "DOWNTREND"
    return "NO_TREND"
