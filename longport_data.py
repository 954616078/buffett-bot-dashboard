"""LongPort OpenAPI data access for candlesticks and depth."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Tuple

import pandas as pd


def _normalize_symbol(symbol: str) -> str:
    s = symbol.strip().upper()
    s = s.replace("-", ".")
    if "." in s:
        suffix = s.rsplit(".", 1)[-1]
        if suffix in {"US", "HK", "SH", "SZ", "SG"}:
            return s
        return f"{s}.US"
    return f"{s}.US"


def _to_float(value) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _to_int(value) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _extract_attr(obj, *names):
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
    return None


def _candles_to_df(candles) -> pd.DataFrame:
    rows = []
    for c in candles:
        ts = _extract_attr(c, "timestamp", "time")
        if isinstance(ts, datetime):
            dt = ts
        else:
            dt = pd.to_datetime(ts, errors="coerce")
        rows.append(
            {
                "Date": dt,
                "Open": _to_float(_extract_attr(c, "open")),
                "High": _to_float(_extract_attr(c, "high")),
                "Low": _to_float(_extract_attr(c, "low")),
                "Close": _to_float(_extract_attr(c, "close", "last_done")),
                "Volume": _to_int(_extract_attr(c, "volume")),
            }
        )
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.dropna(subset=["Date", "Close"]).sort_values("Date").reset_index(drop=True)


def _depth_to_ob(depth, max_levels: int = 20) -> Dict[str, List[Tuple[float, float]]]:
    bids_raw = _extract_attr(depth, "bids") or []
    asks_raw = _extract_attr(depth, "asks") or []

    bids: List[Tuple[float, float]] = []
    asks: List[Tuple[float, float]] = []

    for item in bids_raw[:max_levels]:
        price = _to_float(_extract_attr(item, "price"))
        qty = _to_float(_extract_attr(item, "volume", "quantity"))
        if price > 0 and qty > 0:
            bids.append((price, qty))

    for item in asks_raw[:max_levels]:
        price = _to_float(_extract_attr(item, "price"))
        qty = _to_float(_extract_attr(item, "volume", "quantity"))
        if price > 0 and qty > 0:
            asks.append((price, qty))

    return {"bids": bids, "asks": asks}


class LongPortDataClient:
    """Simple LongPort SDK wrapper with the same shape used by analysis pipeline."""

    def __init__(self) -> None:
        # Lazy import so local script still works when SDK is not installed.
        from longport.openapi import Config, QuoteContext

        self._cfg = Config.from_env()
        self._ctx = QuoteContext(self._cfg)
        self._mod = __import__("longport.openapi", fromlist=["Period", "AdjustType"])

    def fetch_kline_df(self, symbol: str, count: int = 120) -> pd.DataFrame:
        symbol_lp = _normalize_symbol(symbol)
        Period = getattr(self._mod, "Period")
        AdjustType = getattr(self._mod, "AdjustType")
        candles = self._ctx.candlesticks(symbol_lp, Period.Day, count, AdjustType.NoAdjust)
        return _candles_to_df(candles)

    def fetch_orderbook(self, symbol: str, depth: int = 20) -> Dict[str, List[Tuple[float, float]]]:
        symbol_lp = _normalize_symbol(symbol)
        data = self._ctx.depth(symbol_lp)
        return _depth_to_ob(data, max_levels=depth)
