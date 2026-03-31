"""Fetch and parse K-line and lightweight order-book data from Yahoo Finance."""

from __future__ import annotations

import re
from io import StringIO
from typing import Dict, List, Optional, Tuple

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import Browser, Page, Playwright, TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from config import (
    FETCH_TIMEOUT_SECONDS,
    HEADLESS_BROWSER,
    OB_DEPTH,
    TOP_MARKETCAP_SOURCE_URL,
)


class BrowserDataClient:
    """Playwright client that keeps one browser/page for an entire scan run."""

    def __init__(self) -> None:
        self._pw: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None

    def __enter__(self) -> "BrowserDataClient":
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=HEADLESS_BROWSER)
        self._page = self._browser.new_page()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()
        self._page = None
        self._browser = None
        self._pw = None

    def fetch_html(self, url: str) -> str:
        if not self._page:
            raise RuntimeError("BrowserDataClient is not started. Use it as a context manager.")
        try:
            self._page.goto(url, wait_until="domcontentloaded", timeout=FETCH_TIMEOUT_SECONDS * 1000)
            self._page.wait_for_timeout(800)
            return self._page.content()
        except PlaywrightTimeoutError as exc:
            raise RuntimeError(f"Timeout loading {url}") from exc

    def fetch_kline_html(self, stock: str) -> str:
        return self.fetch_html(f"https://finance.yahoo.com/quote/{stock}/history?p={stock}")

    def fetch_orderbook_html(self, stock: str) -> str:
        # Yahoo quote page usually includes Bid/Ask (x Size). It's not full L2 depth,
        # but can still provide a simple order-pressure signal.
        return self.fetch_html(f"https://finance.yahoo.com/quote/{stock}?p={stock}")

    def fetch_top_us_market_cap_tickers(self, limit: int = 100) -> List[str]:
        html = self.fetch_html(TOP_MARKETCAP_SOURCE_URL)
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select("table tbody tr")
        if not rows:
            raise RuntimeError("Failed to parse top market-cap rows")

        tickers: List[str] = []
        for row in rows:
            cols = [td.get_text(" ", strip=True) for td in row.select("td")]
            if len(cols) < 3:
                continue
            ticker = _extract_ticker_from_name(cols[2])
            if ticker:
                tickers.append(ticker)

        # Deduplicate while preserving order.
        deduped = list(dict.fromkeys(tickers))
        return deduped[:limit]


def _fetch_html(url: str) -> str:
    with BrowserDataClient() as client:
        return client.fetch_html(url)


def fetch_kline_html(stock: str) -> str:
    return _fetch_html(f"https://finance.yahoo.com/quote/{stock}/history?p={stock}")


def fetch_orderbook_html(stock: str) -> str:
    # Yahoo quote page usually includes Bid/Ask (x Size). It's not full L2 depth,
    # but can still provide a simple order-pressure signal.
    return _fetch_html(f"https://finance.yahoo.com/quote/{stock}?p={stock}")


def _extract_ticker_from_name(name_value: str) -> str:
    # Examples from source table cell:
    # "NVIDIA NVDA" -> NVDA
    # "Berkshire Hathaway BRK-B" -> BRK-B
    value = str(name_value).strip()
    m = re.search(r"([A-Z][A-Z0-9.\-]{0,7})\s*$", value)
    if not m:
        return ""
    ticker = m.group(1)
    # Filter obvious false positives.
    if not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,7}", ticker):
        return ""
    return ticker


def parse_kline_html(html: str) -> pd.DataFrame:
    tables = pd.read_html(StringIO(html))
    if not tables:
        raise ValueError("No tables found in K-line page")

    history = None
    for table in tables:
        if "Date" in table.columns and any("Close" in str(col) for col in table.columns):
            history = table.copy()
            break

    if history is None:
        raise ValueError("Could not locate Yahoo historical table")

    close_col = next(col for col in history.columns if "Close" in str(col))
    numeric_cols = ["Open", "High", "Low", close_col, "Volume"]

    # Remove dividend/split rows which are non-price events.
    history = history[~history["Date"].astype(str).str.contains("Dividend|Split", case=False, na=False)]

    history["Date"] = pd.to_datetime(history["Date"], errors="coerce")
    for col in numeric_cols:
        if col in history.columns:
            history[col] = (
                history[col]
                .astype(str)
                .str.replace(",", "", regex=False)
                .str.replace("-", "", regex=False)
            )
            history[col] = pd.to_numeric(history[col], errors="coerce")

    history = history.rename(columns={close_col: "Close"})
    history = history.dropna(subset=["Date", "Close"]).sort_values("Date").reset_index(drop=True)
    return history[["Date", "Open", "High", "Low", "Close", "Volume"]].copy()


def _extract_bid_ask_text(html: str) -> Tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    bid_match = re.search(r"Bid\s+([0-9.,]+\s*x\s*[0-9.,]+)", text, re.IGNORECASE)
    ask_match = re.search(r"Ask\s+([0-9.,]+\s*x\s*[0-9.,]+)", text, re.IGNORECASE)

    bid_text = bid_match.group(1) if bid_match else ""
    ask_text = ask_match.group(1) if ask_match else ""
    return bid_text, ask_text


def _parse_price_size(value: str) -> Tuple[float, float]:
    # Expected format like: "233.10 x 800"
    m = re.search(r"([0-9.,]+)\s*x\s*([0-9.,]+)", value)
    if not m:
        return 0.0, 0.0
    price = float(m.group(1).replace(",", ""))
    qty = float(m.group(2).replace(",", ""))
    return price, qty


def parse_orderbook_html(html: str, depth: int = OB_DEPTH) -> Dict[str, List[Tuple[float, float]]]:
    bid_text, ask_text = _extract_bid_ask_text(html)
    bid_price, bid_qty = _parse_price_size(bid_text)
    ask_price, ask_qty = _parse_price_size(ask_text)

    bids: List[Tuple[float, float]] = []
    asks: List[Tuple[float, float]] = []

    # Yahoo only exposes a top level in this view. We keep the same shape as
    # multi-level order book for compatibility with analysis logic.
    if bid_price > 0 and bid_qty > 0:
        bids = [(bid_price, bid_qty)]
    if ask_price > 0 and ask_qty > 0:
        asks = [(ask_price, ask_qty)]

    return {"bids": bids[:depth], "asks": asks[:depth]}
