"""Paper trading engine with adaptive position sizing."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from config import (
    DB_PATH,
    PAPER_INITIAL_CASH,
    PAPER_BASE_RISK_PCT,
    PAPER_LEARN_LOOKBACK,
    PAPER_MAX_POSITION_PCT,
    PAPER_MAX_POSITIONS,
    PAPER_MAX_RISK_PCT,
    PAPER_MIN_RISK_PCT,
    PAPER_STOP_LOSS_PCT,
    PAPER_TAKE_PROFIT_PCT,
    MAX_HOLD_DAYS,
)
from portfolio_analytics import get_risk_status
from runtime_settings import get_settings, init_runtime_settings


@dataclass
class Position:
    symbol: str
    qty: int
    avg_cost: float


@dataclass
class TradeAction:
    symbol: str
    action: str
    qty: int
    price: float
    reason: str
    realized_pnl: float


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class PaperTrader:
    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path
        init_runtime_settings()
        self._load_runtime()
        self._init_schema()
        self._ensure_account()

    def _load_runtime(self) -> None:
        settings = get_settings(
            {
                "paper_base_risk_pct": PAPER_BASE_RISK_PCT,
                "paper_min_risk_pct": PAPER_MIN_RISK_PCT,
                "paper_max_risk_pct": PAPER_MAX_RISK_PCT,
                "paper_stop_loss_pct": PAPER_STOP_LOSS_PCT,
                "paper_take_profit_pct": PAPER_TAKE_PROFIT_PCT,
                "paper_max_position_pct": PAPER_MAX_POSITION_PCT,
                "paper_learn_lookback": PAPER_LEARN_LOOKBACK,
                "paper_max_positions": PAPER_MAX_POSITIONS,
                "max_hold_days": MAX_HOLD_DAYS,
                "daily_loss_limit_pct": 0.03,
                "max_drawdown_limit_pct": 0.12,
                "enable_circuit_breaker": True,
            }
        )
        self.paper_base_risk_pct = float(settings["paper_base_risk_pct"])
        self.paper_min_risk_pct = float(settings["paper_min_risk_pct"])
        self.paper_max_risk_pct = float(settings["paper_max_risk_pct"])
        self.paper_stop_loss_pct = float(settings["paper_stop_loss_pct"])
        self.paper_take_profit_pct = float(settings["paper_take_profit_pct"])
        self.paper_max_position_pct = float(settings["paper_max_position_pct"])
        self.paper_learn_lookback = int(settings["paper_learn_lookback"])
        self.paper_max_positions = int(settings["paper_max_positions"])
        self.max_hold_days = int(settings["max_hold_days"])
        self.daily_loss_limit_pct = float(settings["daily_loss_limit_pct"])
        self.max_drawdown_limit_pct = float(settings["max_drawdown_limit_pct"])
        self.enable_circuit_breaker = bool(settings["enable_circuit_breaker"])

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS paper_account(
                    id INTEGER PRIMARY KEY CHECK (id=1),
                    cash REAL NOT NULL,
                    equity REAL NOT NULL,
                    risk_pct REAL NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS paper_positions(
                    symbol TEXT PRIMARY KEY,
                    qty INTEGER NOT NULL,
                    avg_cost REAL NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS paper_orders(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    qty INTEGER NOT NULL,
                    price REAL NOT NULL,
                    notional REAL NOT NULL,
                    reason TEXT NOT NULL,
                    realized_pnl REAL NOT NULL,
                    cash_after REAL NOT NULL,
                    equity_after REAL NOT NULL,
                    risk_pct_after REAL NOT NULL
                )
                """
            )
            # Backward-compatible migration for older DBs that were created
            # before some columns existed.
            columns = {
                str(row[1])
                for row in conn.execute("PRAGMA table_info(paper_orders)").fetchall()
            }
            required_columns = {
                "notional": "REAL NOT NULL DEFAULT 0",
                "reason": "TEXT NOT NULL DEFAULT ''",
                "realized_pnl": "REAL NOT NULL DEFAULT 0",
                "cash_after": "REAL NOT NULL DEFAULT 0",
                "equity_after": "REAL NOT NULL DEFAULT 0",
                "risk_pct_after": "REAL NOT NULL DEFAULT 0",
            }
            for name, ddl in required_columns.items():
                if name not in columns:
                    conn.execute(f"ALTER TABLE paper_orders ADD COLUMN {name} {ddl}")
            conn.commit()

    def _ensure_account(self) -> None:
        with self._connect() as conn:
            row = conn.execute("SELECT id FROM paper_account WHERE id=1").fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO paper_account(id,cash,equity,risk_pct,updated_at) VALUES(1,?,?,?,?)",
                    (PAPER_INITIAL_CASH, PAPER_INITIAL_CASH, self.paper_base_risk_pct, _now()),
                )
                conn.commit()

    def _get_account(self, conn: sqlite3.Connection) -> Dict[str, float]:
        row = conn.execute(
            "SELECT cash,equity,risk_pct FROM paper_account WHERE id=1"
        ).fetchone()
        if not row:
            raise RuntimeError("paper_account is not initialized")
        return {"cash": float(row[0]), "equity": float(row[1]), "risk_pct": float(row[2])}

    def _set_account(self, conn: sqlite3.Connection, cash: float, equity: float, risk_pct: float) -> None:
        conn.execute(
            "UPDATE paper_account SET cash=?,equity=?,risk_pct=?,updated_at=? WHERE id=1",
            (cash, equity, risk_pct, _now()),
        )

    def _get_position(self, conn: sqlite3.Connection, symbol: str) -> Optional[Position]:
        row = conn.execute(
            "SELECT symbol,qty,avg_cost FROM paper_positions WHERE symbol=?",
            (symbol,),
        ).fetchone()
        if not row:
            return None
        return Position(symbol=row[0], qty=int(row[1]), avg_cost=float(row[2]))

    def _upsert_position(self, conn: sqlite3.Connection, symbol: str, qty: int, avg_cost: float) -> None:
        if qty <= 0:
            conn.execute("DELETE FROM paper_positions WHERE symbol=?", (symbol,))
            return
        conn.execute(
            """
            INSERT INTO paper_positions(symbol,qty,avg_cost,updated_at)
            VALUES(?,?,?,?)
            ON CONFLICT(symbol) DO UPDATE SET
                qty=excluded.qty,
                avg_cost=excluded.avg_cost,
                updated_at=excluded.updated_at
            """,
            (symbol, qty, avg_cost, _now()),
        )

    def _mark_to_market_equity(self, conn: sqlite3.Connection, prices: Dict[str, float], cash: float) -> float:
        rows = conn.execute("SELECT symbol,qty FROM paper_positions").fetchall()
        market_value = 0.0
        for sym, qty in rows:
            px = float(prices.get(sym, 0.0))
            if px > 0:
                market_value += int(qty) * px
        return cash + market_value

    def _learn_risk_pct(self, conn: sqlite3.Connection, current: float) -> float:
        rows = conn.execute(
            "SELECT realized_pnl FROM paper_orders WHERE action='SELL' ORDER BY id DESC LIMIT ?",
            (self.paper_learn_lookback,),
        ).fetchall()
        if not rows:
            return current
        wins = sum(1 for (pnl,) in rows if float(pnl) > 0)
        total = len(rows)
        win_rate = wins / total if total else 0.0

        next_risk = current
        if win_rate >= 0.6:
            next_risk = min(self.paper_max_risk_pct, current + 0.001)
        elif win_rate <= 0.4:
            next_risk = max(self.paper_min_risk_pct, current - 0.001)
        return next_risk

    def _insert_order(
        self,
        conn: sqlite3.Connection,
        action: TradeAction,
        cash_after: float,
        equity_after: float,
        risk_pct_after: float,
    ) -> None:
        conn.execute(
            """
            INSERT INTO paper_orders(
                ts,symbol,action,qty,price,notional,reason,realized_pnl,cash_after,equity_after,risk_pct_after
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                _now(),
                action.symbol,
                action.action,
                action.qty,
                action.price,
                action.qty * action.price,
                action.reason,
                action.realized_pnl,
                cash_after,
                equity_after,
                risk_pct_after,
            ),
        )

    def on_signal(self, symbol: str, price: float, trend: str, ob_signal: str) -> Optional[TradeAction]:
        if price <= 0:
            return None

        with self._connect() as conn:
            account = self._get_account(conn)
            cash = account["cash"]
            equity = account["equity"]
            risk_pct = account["risk_pct"]
            pos = self._get_position(conn, symbol)

            rule_a = trend == "UPTREND" and ob_signal == "BUY_PRESSURE"
            rule_b = trend == "DOWNTREND" and ob_signal == "SELL_PRESSURE"

            # Existing position: check exits first.
            if pos is not None:
                stop_px = pos.avg_cost * (1.0 - self.paper_stop_loss_pct)
                tp_px = pos.avg_cost * (1.0 + self.paper_take_profit_pct)
                
                # Check time-based exit (MAX_HOLD_DAYS)
                from datetime import datetime, timedelta
                try:
                    buy_time = datetime.strptime(pos.updated_at, "%Y-%m-%d %H:%M:%S")
                    days_held = (datetime.now() - buy_time).days
                    if days_held >= self.max_hold_days:
                        proceeds = pos.qty * price
                        realized = (price - pos.avg_cost) * pos.qty
                        cash += proceeds
                        self._upsert_position(conn, symbol, 0, 0.0)
                        next_equity = self._mark_to_market_equity(conn, {symbol: price}, cash)
                        next_risk = self._learn_risk_pct(conn, risk_pct)
                        action = TradeAction(symbol, "SELL", pos.qty, price, f"TIME_EXIT_{days_held}d", realized)
                        self._insert_order(conn, action, cash, next_equity, next_risk)
                        self._set_account(conn, cash, next_equity, next_risk)
                        conn.commit()
                        return action
                except:
                    pass
                
                if price <= stop_px:
                    proceeds = pos.qty * price
                    realized = (price - pos.avg_cost) * pos.qty
                    cash += proceeds
                    self._upsert_position(conn, symbol, 0, 0.0)
                    next_equity = self._mark_to_market_equity(conn, {symbol: price}, cash)
                    next_risk = self._learn_risk_pct(conn, risk_pct)
                    action = TradeAction(symbol, "SELL", pos.qty, price, "STOP_LOSS", realized)
                    self._insert_order(conn, action, cash, next_equity, next_risk)
                    self._set_account(conn, cash, next_equity, next_risk)
                    conn.commit()
                    return action
                if price >= tp_px:
                    proceeds = pos.qty * price
                    realized = (price - pos.avg_cost) * pos.qty
                    cash += proceeds
                    self._upsert_position(conn, symbol, 0, 0.0)
                    next_equity = self._mark_to_market_equity(conn, {symbol: price}, cash)
                    next_risk = self._learn_risk_pct(conn, risk_pct)
                    action = TradeAction(symbol, "SELL", pos.qty, price, "TAKE_PROFIT", realized)
                    self._insert_order(conn, action, cash, next_equity, next_risk)
                    self._set_account(conn, cash, next_equity, next_risk)
                    conn.commit()
                    return action

                # Rule B exit.
                if rule_b:
                    proceeds = pos.qty * price
                    realized = (price - pos.avg_cost) * pos.qty
                    cash += proceeds
                    self._upsert_position(conn, symbol, 0, 0.0)
                    next_equity = self._mark_to_market_equity(conn, {symbol: price}, cash)
                    next_risk = self._learn_risk_pct(conn, risk_pct)
                    action = TradeAction(symbol, "SELL", pos.qty, price, "RULE_B_EXIT", realized)
                    self._insert_order(conn, action, cash, next_equity, next_risk)
                    self._set_account(conn, cash, next_equity, next_risk)
                    conn.commit()
                    return action

            # Rule A entry (only if no position).
            if pos is None and rule_a:
                risk_state = get_risk_status(conn, equity)
                if not risk_state["can_open_new_positions"]:
                    return None
                current_positions = conn.execute("SELECT COUNT(*) FROM paper_positions").fetchone()
                position_count = int(current_positions[0]) if current_positions else 0
                if position_count >= self.paper_max_positions:
                    return None
                risk_budget = equity * risk_pct
                qty_by_risk = int(risk_budget / (price * max(self.paper_stop_loss_pct, 1e-6)))
                qty_by_alloc = int((equity * self.paper_max_position_pct) / price)
                qty = max(0, min(qty_by_risk, qty_by_alloc))
                notional = qty * price
                if qty >= 1 and notional <= cash:
                    cash -= notional
                    self._upsert_position(conn, symbol, qty, price)
                    next_equity = self._mark_to_market_equity(conn, {symbol: price}, cash)
                    next_risk = self._learn_risk_pct(conn, risk_pct)
                    action = TradeAction(symbol, "BUY", qty, price, "RULE_A_ENTRY", 0.0)
                    self._insert_order(conn, action, cash, next_equity, next_risk)
                    self._set_account(conn, cash, next_equity, next_risk)
                    conn.commit()
                    return action

            # No trade, but refresh equity and risk.
            next_equity = self._mark_to_market_equity(conn, {symbol: price}, cash)
            self._set_account(conn, cash, next_equity, risk_pct)
            conn.commit()
            return None

    def snapshot(self) -> Dict[str, object]:
        with self._connect() as conn:
            account = self._get_account(conn)
            pos_rows = conn.execute(
                "SELECT symbol,qty,avg_cost FROM paper_positions ORDER BY symbol"
            ).fetchall()
            positions = [
                {"symbol": s, "qty": int(q), "avg_cost": float(c)} for s, q, c in pos_rows
            ]
            risk_state = get_risk_status(conn, float(account["equity"]))
            return {
                "cash": account["cash"],
                "equity": account["equity"],
                "risk_pct": account["risk_pct"],
                "positions": positions,
                "risk_state": risk_state,
            }
