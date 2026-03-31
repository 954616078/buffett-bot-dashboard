"""SQLite helpers for scan logs."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Optional

from config import DB_PATH


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trades(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                stock TEXT NOT NULL,
                last_price REAL,
                trend TEXT NOT NULL,
                ob_signal TEXT NOT NULL,
                ai_analysis TEXT NOT NULL
            )
            """
        )
        conn.commit()


def save_trade(stock: str, last_price: float, trend: str, ob_signal: str, ai_analysis: str, at: Optional[str] = None) -> None:
    ts = at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO trades(date, stock, last_price, trend, ob_signal, ai_analysis) VALUES (?,?,?,?,?,?)",
            (ts, stock, last_price, trend, ob_signal, ai_analysis),
        )
        conn.commit()
