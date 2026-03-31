"""Runtime-overridable settings persisted in SQLite."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from config import DB_PATH


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def init_runtime_settings() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runtime_settings(
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def set_setting(key: str, value: Any) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO runtime_settings(key, value, updated_at)
            VALUES(?,?,?)
            ON CONFLICT(key) DO UPDATE SET
                value=excluded.value,
                updated_at=excluded.updated_at
            """,
            (key, str(value), _now()),
        )
        conn.commit()


def get_setting(key: str, default: Any) -> Any:
    try:
        with _connect() as conn:
            row = conn.execute("SELECT value FROM runtime_settings WHERE key=?", (key,)).fetchone()
    except sqlite3.Error:
        return default

    if not row:
        return default
    raw = row[0]
    if isinstance(default, bool):
        return str(raw).lower() in {"1", "true", "yes", "on"}
    if isinstance(default, int):
        try:
            return int(float(raw))
        except (TypeError, ValueError):
            return default
    if isinstance(default, float):
        try:
            return float(raw)
        except (TypeError, ValueError):
            return default
    return str(raw)


def get_settings(keys_with_defaults: dict[str, Any]) -> dict[str, Any]:
    return {key: get_setting(key, default) for key, default in keys_with_defaults.items()}
