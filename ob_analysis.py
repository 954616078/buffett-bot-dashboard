"""Order-book pressure analysis."""

from __future__ import annotations

from typing import Dict, List, Tuple


OrderBook = Dict[str, List[Tuple[float, float]]]


def analyze_orderbook(ob_data: OrderBook, imbalance_threshold: float = 1.2) -> str:
    bids = sum(float(qty) for _, qty in ob_data.get("bids", []))
    asks = sum(float(qty) for _, qty in ob_data.get("asks", []))

    if bids == 0 and asks == 0:
        return "NO_OB_DATA"
    if bids > asks * imbalance_threshold:
        return "BUY_PRESSURE"
    if asks > bids * imbalance_threshold:
        return "SELL_PRESSURE"
    return "NEUTRAL"
