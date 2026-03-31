"""Seed the SQLite DB with baseline data when tables are empty."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


def _is_empty(conn: sqlite3.Connection) -> bool:
    try:
        row = conn.execute("SELECT COUNT(*) FROM trades").fetchone()
    except sqlite3.Error:
        return True
    return bool(row and int(row[0]) == 0)


def seed_if_empty(db_path: str, seed_path: str) -> bool:
    seed_file = Path(seed_path)
    if not seed_file.exists():
        return False

    with sqlite3.connect(db_path) as conn:
        if not _is_empty(conn):
            return False

        payload = json.loads(seed_file.read_text(encoding="utf-8"))

        for row in payload.get("trades", []):
            conn.execute(
                "INSERT INTO trades(date,stock,last_price,trend,ob_signal,ai_analysis) VALUES (?,?,?,?,?,?)",
                (
                    row.get("date", ""),
                    row.get("stock", ""),
                    row.get("last_price"),
                    row.get("trend", "UNKNOWN"),
                    row.get("ob_signal", "UNKNOWN"),
                    row.get("ai_analysis", ""),
                ),
            )

        for row in payload.get("paper_account", []):
            conn.execute(
                """
                INSERT OR REPLACE INTO paper_account(id,cash,equity,risk_pct,updated_at)
                VALUES(?,?,?,?,?)
                """,
                (
                    int(row.get("id", 1)),
                    float(row.get("cash", 0.0)),
                    float(row.get("equity", 0.0)),
                    float(row.get("risk_pct", 0.0)),
                    row.get("updated_at", ""),
                ),
            )

        for row in payload.get("paper_positions", []):
            conn.execute(
                """
                INSERT OR REPLACE INTO paper_positions(symbol,qty,avg_cost,updated_at)
                VALUES(?,?,?,?)
                """,
                (
                    row.get("symbol", ""),
                    int(row.get("qty", 0)),
                    float(row.get("avg_cost", 0.0)),
                    row.get("updated_at", ""),
                ),
            )

        for row in payload.get("paper_orders", []):
            conn.execute(
                """
                INSERT INTO paper_orders(
                    ts,symbol,action,qty,price,notional,reason,realized_pnl,cash_after,equity_after,risk_pct_after
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    row.get("ts", ""),
                    row.get("symbol", ""),
                    row.get("action", ""),
                    int(row.get("qty", 0)),
                    float(row.get("price", 0.0)),
                    float(row.get("notional", 0.0)),
                    row.get("reason", ""),
                    float(row.get("realized_pnl", 0.0)),
                    float(row.get("cash_after", 0.0)),
                    float(row.get("equity_after", 0.0)),
                    float(row.get("risk_pct_after", 0.0)),
                ),
            )

        conn.commit()
        return True
