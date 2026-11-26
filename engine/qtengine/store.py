"""Tiny SQLite persistence for the journal and account config (swap for Postgres/Timescale in prod)."""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("QT_DB", Path(__file__).resolve().parents[2] / "data" / "quantrader.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account TEXT NOT NULL DEFAULT 'main',
    source TEXT NOT NULL DEFAULT 'manual',      -- manual | live | paper | demo-synthetic
    date TEXT NOT NULL, entry_time TEXT NOT NULL, exit_time TEXT NOT NULL,
    symbol TEXT NOT NULL DEFAULT 'MES', strategy TEXT, side INTEGER NOT NULL,
    contracts INTEGER NOT NULL DEFAULT 1, entry REAL, exit REAL, stop REAL,
    risk_dollars REAL, pnl REAL NOT NULL, r_net REAL, exit_reason TEXT,
    mae_r REAL, mfe_r REAL, notes TEXT, tags TEXT
);
CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""

TRADE_COLS = ["account", "source", "date", "entry_time", "exit_time", "symbol", "strategy", "side", "contracts",
              "entry", "exit", "stop", "risk_dollars", "pnl", "r_net", "exit_reason", "mae_r", "mfe_r", "notes", "tags"]


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def insert_trades(rows: list[dict]) -> int:
    with connect() as con:
        for r in rows:
            vals = [json.dumps(r.get(c)) if c == "tags" and r.get(c) is not None else r.get(c) for c in TRADE_COLS]
            vals[0] = vals[0] or "main"
            vals[1] = vals[1] or "manual"
            con.execute(f"INSERT INTO trades ({','.join(TRADE_COLS)}) VALUES ({','.join('?' * len(TRADE_COLS))})", vals)
    return len(rows)


def list_trades(account: str = "main") -> list[dict]:
    with connect() as con:
        rows = con.execute("SELECT * FROM trades WHERE account=? ORDER BY date, entry_time", (account,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["tags"] = json.loads(d["tags"]) if d.get("tags") else []
        out.append(d)
    return out


def clear_trades(account: str = "main", source: str | None = None) -> None:
    with connect() as con:
        if source:
            con.execute("DELETE FROM trades WHERE account=? AND source=?", (account, source))
        else:
            con.execute("DELETE FROM trades WHERE account=?", (account,))


def get_config(key: str, default=None):
    with connect() as con:
        row = con.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
    return json.loads(row["value"]) if row else default


def set_config(key: str, value) -> None:
    with connect() as con:
        con.execute("INSERT INTO config(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key, json.dumps(value)))
