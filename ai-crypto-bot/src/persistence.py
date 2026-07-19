from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.trading.paper import Trade


class SQLitePersistence:
    CONFIG_HASH_KEY = "config_hash"

    def __init__(self, db_path: str, config_hash: str = "") -> None:
        self.db_path = db_path
        self.config_hash = config_hash
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_db()
        self._check_config_invalidation()

    def _init_db(self) -> None:
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                direction TEXT NOT NULL,
                price REAL NOT NULL,
                size REAL NOT NULL,
                pnl REAL DEFAULT 0,
                entry_price REAL,
                opened_at TEXT,
                closed_at TEXT
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS equity_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                equity REAL NOT NULL,
                cash REAL NOT NULL
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS cycle_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                summary TEXT NOT NULL,
                symbols_checked INT DEFAULT 0,
                trades_executed INT DEFAULT 0,
                errors INT DEFAULT 0,
                duration_ms INT DEFAULT 0,
                next_run_at TEXT
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                symbol TEXT NOT NULL,
                price REAL NOT NULL
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS alert_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                message TEXT NOT NULL,
                level TEXT NOT NULL DEFAULT 'info'
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS signal_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                signal TEXT NOT NULL,
                price REAL NOT NULL,
                fast_sma REAL,
                slow_sma REAL,
                timestamp TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS ohlc_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL DEFAULT 0,
                UNIQUE(timestamp, symbol)
            )
        """)
        self._conn.commit()

    def save_trade(self, trade: Trade) -> None:
        self._conn.execute(
            "INSERT INTO trades (symbol, side, direction, price, size, pnl, entry_price) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (trade.symbol, trade.side, trade.direction,
             trade.price, trade.size, trade.pnl, trade.entry_price),
        )
        self._conn.commit()

    def save_state(self, balance: float, positions: dict[str, dict[str, Any]]) -> None:
        self._conn.execute(
            "REPLACE INTO state (key, value) VALUES ('balance', ?)",
            (str(balance),),
        )
        self._conn.execute(
            "REPLACE INTO state (key, value) VALUES ('positions', ?)",
            (json.dumps(positions) if positions else "{}",),
        )
        self._conn.commit()

    def _check_config_invalidation(self) -> None:
        cursor = self._conn.execute(
            "SELECT value FROM state WHERE key = ?", (self.CONFIG_HASH_KEY,)
        )
        row = cursor.fetchone()
        stored_hash = str(row[0]) if row else ""
        if self.config_hash and stored_hash and stored_hash != self.config_hash:
            self._clear_state()
        if self.config_hash:
            self._conn.execute(
                "REPLACE INTO state (key, value) VALUES (?, ?)",
                (self.CONFIG_HASH_KEY, self.config_hash),
            )
            self._conn.commit()

    def _clear_state(self) -> None:
        cursor = self._conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cursor.fetchall()
                  if r[0] not in ("state", "trades")]
        for t in tables:
            self._conn.execute(f"DELETE FROM {t}")
        self._conn.execute("DELETE FROM state WHERE key != ?", (self.CONFIG_HASH_KEY,))
        self._conn.execute("DELETE FROM trades")
        self._conn.commit()

    def save_initial_capital(self, capital: float) -> None:
        self._conn.execute(
            "REPLACE INTO state (key, value) VALUES ('initial_capital', ?)",
            (str(capital),),
        )
        self._conn.commit()

    def save_challenge_state(self, restarts: int, failures: int, start_date: str, target: float) -> None:
        self._conn.execute("REPLACE INTO state (key, value) VALUES ('challenge_restarts', ?)", (str(restarts),))
        self._conn.execute("REPLACE INTO state (key, value) VALUES ('challenge_failures', ?)", (str(failures),))
        self._conn.execute("REPLACE INTO state (key, value) VALUES ('challenge_start', ?)", (start_date,))
        self._conn.execute("REPLACE INTO state (key, value) VALUES ('challenge_target', ?)", (str(target),))
        self._conn.commit()

    def load_challenge_state(self) -> dict:
        cursor = self._conn.execute("SELECT key, value FROM state WHERE key LIKE 'challenge_%'")
        state = {'restarts': 0, 'failures': 0, 'start': '', 'target': 1000.0}
        for k, v in cursor.fetchall():
            if k == 'challenge_restarts': state['restarts'] = int(v)
            elif k == 'challenge_failures': state['failures'] = int(v)
            elif k == 'challenge_start': state['start'] = v
            elif k == 'challenge_target': state['target'] = float(v)
        return state

    def save_prices(self, prices: dict[str, float]) -> None:
        self._conn.execute(
            "REPLACE INTO state (key, value) VALUES ('prices', ?)",
            (json.dumps(prices),),
        )
        self._conn.commit()

    def load_prices(self) -> dict[str, float]:
        cursor = self._conn.execute("SELECT value FROM state WHERE key = 'prices'")
        row = cursor.fetchone()
        return json.loads(row["value"]) if row else {}

    def save_equity_snapshot(self, equity: float, cash: float) -> None:
        self._conn.execute(
            "INSERT INTO equity_snapshots (equity, cash) VALUES (?, ?)",
            (round(equity, 2), round(cash, 2)),
        )
        self._conn.commit()

    def load_equity_snapshots(self) -> list[dict[str, Any]]:
        cursor = self._conn.execute(
            "SELECT id, timestamp, equity, cash FROM equity_snapshots ORDER BY id ASC",
        )
        return [dict(r) for r in cursor.fetchall()]

    def save_heartbeat(self, next_run_at: str) -> None:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self._conn.execute(
            "REPLACE INTO state (key, value) VALUES ('heartbeat', ?)", (now,),
        )
        self._conn.execute(
            "REPLACE INTO state (key, value) VALUES ('next_run_at', ?)", (next_run_at,),
        )
        self._conn.commit()

    def save_cycle_log(self, summary: str, symbols_checked: int,
                       trades_executed: int, errors: int,
                       duration_ms: int, next_run_at: str) -> None:
        self._conn.execute(
            "INSERT INTO cycle_log (summary, symbols_checked, trades_executed, "
            "errors, duration_ms, next_run_at) VALUES (?, ?, ?, ?, ?, ?)",
            (summary, symbols_checked, trades_executed, errors, duration_ms, next_run_at),
        )
        self._conn.commit()

        cursor = self._conn.execute("SELECT COUNT(*) FROM cycle_log")
        count = cursor.fetchone()[0]
        if count > 50:
            self._conn.execute(
                "DELETE FROM cycle_log WHERE id NOT IN "
                "(SELECT id FROM cycle_log ORDER BY id DESC LIMIT 50)",
            )
            self._conn.commit()

    def save_price_snapshot(self, symbol: str, price: float) -> None:
        self._conn.execute(
            "INSERT INTO price_history (symbol, price) VALUES (?, ?)",
            (symbol, round(price, 2)),
        )
        self._conn.commit()
        cursor = self._conn.execute("SELECT COUNT(*) FROM price_history")
        if cursor.fetchone()[0] > 500:
            self._conn.execute(
                "DELETE FROM price_history WHERE id NOT IN "
                "(SELECT id FROM price_history ORDER BY id DESC LIMIT 500)",
            )
            self._conn.commit()

    def load_price_history(self, symbol: str, limit: int = 100) -> list[dict[str, Any]]:
        cursor = self._conn.execute(
            "SELECT id, timestamp, price FROM price_history "
            "WHERE symbol = ? ORDER BY id ASC LIMIT ?",
            (symbol, limit),
        )
        return [dict(r) for r in cursor.fetchall()]

    def save_signal_log(self, cycle_id: int, symbol: str, signal: str,
                         price: float, fast_sma: float, slow_sma: float) -> None:
        self._conn.execute(
            "INSERT INTO signal_log (cycle_id, symbol, signal, price, fast_sma, slow_sma) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (cycle_id, symbol, signal, round(price, 2),
             round(fast_sma, 2), round(slow_sma, 2)),
        )
        self._conn.commit()

    def load_latest_signals(self) -> list[dict[str, Any]]:
        cursor = self._conn.execute(
            "SELECT * FROM signal_log WHERE cycle_id = (SELECT MAX(cycle_id) FROM signal_log) "
            "ORDER BY symbol",
        )
        return [dict(r) for r in cursor.fetchall()]

    def save_ohlc(self, symbol: str, ohlc: dict) -> None:
        ts = ohlc.get("timestamp", datetime.now(timezone.utc).isoformat())
        self._conn.execute(
            "INSERT OR REPLACE INTO ohlc_snapshots (timestamp, symbol, open, high, low, close, volume) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ts, symbol, ohlc["open"], ohlc["high"], ohlc["low"], ohlc["close"], ohlc.get("volume", 0)),
        )
        self._conn.commit()
        cursor = self._conn.execute("SELECT COUNT(*) FROM ohlc_snapshots WHERE symbol = ?", (symbol,))
        if cursor.fetchone()[0] > 500:
            self._conn.execute(
                "DELETE FROM ohlc_snapshots WHERE id NOT IN "
                "(SELECT id FROM ohlc_snapshots WHERE symbol = ? ORDER BY id DESC LIMIT 500)",
                (symbol,),
            )
            self._conn.commit()

    def load_ohlc(self, symbol: str, limit: int = 100) -> list[dict]:
        cursor = self._conn.execute(
            "SELECT * FROM ohlc_snapshots WHERE symbol = ? ORDER BY id ASC LIMIT ?",
            (symbol, limit),
        )
        return [dict(r) for r in cursor.fetchall()]

    def save_alert_log(self, message: str, level: str = "info") -> None:
        self._conn.execute(
            "INSERT INTO alert_log (message, level) VALUES (?, ?)",
            (message, level),
        )
        self._conn.commit()
        cursor = self._conn.execute("SELECT COUNT(*) FROM alert_log")
        if cursor.fetchone()[0] > 100:
            self._conn.execute(
                "DELETE FROM alert_log WHERE id NOT IN "
                "(SELECT id FROM alert_log ORDER BY id DESC LIMIT 100)",
            )
            self._conn.commit()

    def load_alerts(self, limit: int = 20) -> list[dict[str, Any]]:
        cursor = self._conn.execute(
            "SELECT * FROM alert_log ORDER BY id DESC LIMIT ?", (limit,),
        )
        return [dict(r) for r in cursor.fetchall()]

    def load_recent_cycles(self, limit: int = 10) -> list[dict[str, Any]]:
        cursor = self._conn.execute(
            "SELECT * FROM cycle_log ORDER BY id DESC LIMIT ?", (limit,),
        )
        return [dict(r) for r in cursor.fetchall()]

    def load_state(self) -> tuple[float, dict[str, Any]]:
        balance = 0.0
        positions: dict[str, Any] = {}
        cursor = self._conn.execute("SELECT key, value FROM state")
        for key, value in cursor.fetchall():
            if key == "balance":
                balance = float(value)
            elif key == "positions":
                positions = json.loads(value) if value else {}
        return balance, positions

    def close(self) -> None:
        self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        self._conn.close()

    def __enter__(self) -> SQLitePersistence:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
