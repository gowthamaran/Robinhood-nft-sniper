from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from sniper.config import app_home, ensure_layout
from sniper.models import MintState, require_transition


class StateStore:
    def __init__(self, root: Path | None = None) -> None:
        root = ensure_layout(root or app_home())
        self.path = root / "state" / "sniper.sqlite3"
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wallet TEXT NOT NULL,
                    contract TEXT NOT NULL,
                    state TEXT NOT NULL,
                    nonce INTEGER,
                    tx_hash TEXT,
                    timings_json TEXT NOT NULL DEFAULT '{}',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS one_broadcast_per_nonce
                ON runs(wallet, contract, nonce)
                WHERE nonce IS NOT NULL AND state IN ('SIGNED','BROADCAST','PENDING','CONFIRMED');
                """
            )
        self.path.chmod(0o600)

    def create_run(self, wallet: str, contract: str) -> int:
        now = time.time()
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO runs(wallet, contract, state, created_at, updated_at) "
                "VALUES(?,?,?,?,?)",
                (wallet.lower(), contract.lower(), MintState.IDLE, now, now),
            )
            assert cursor.lastrowid is not None
            return int(cursor.lastrowid)

    def transition(
        self,
        run_id: int,
        new: MintState,
        *,
        nonce: int | None = None,
        tx_hash: str | None = None,
        timings: dict[str, float] | None = None,
    ) -> None:
        with self._connect() as connection:
            row = connection.execute("SELECT state FROM runs WHERE id=?", (run_id,)).fetchone()
            if row is None:
                raise KeyError(f"Unknown run {run_id}")
            require_transition(MintState(row["state"]), new)
            connection.execute(
                """UPDATE runs SET state=?, nonce=COALESCE(?, nonce), tx_hash=COALESCE(?, tx_hash),
                   timings_json=COALESCE(?, timings_json), updated_at=? WHERE id=?""",
                (
                    new,
                    nonce,
                    tx_hash,
                    json.dumps(timings) if timings is not None else None,
                    time.time(),
                    run_id,
                ),
            )

    def already_broadcast(self, wallet: str, contract: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT 1 FROM runs WHERE wallet=? AND contract=?
                   AND state IN ('SIGNED','BROADCAST','PENDING','CONFIRMED') LIMIT 1""",
                (wallet.lower(), contract.lower()),
            ).fetchone()
            return row is not None

    def last_runs(self, limit: int = 10) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]
