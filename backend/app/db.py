"""SQLite persistence: assessments plus an append-only audit log."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator, Optional

from .models import Assessment

SCHEMA = """
CREATE TABLE IF NOT EXISTS assessments (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    score INTEGER NOT NULL,
    data TEXT NOT NULL,
    paypal_order_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_order ON assessments(paypal_order_id);
CREATE TABLE IF NOT EXISTS webhook_events (
    event_id TEXT PRIMARY KEY,
    received_at TEXT NOT NULL,
    event_type TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    assessment_id TEXT NOT NULL,
    at TEXT NOT NULL,
    event TEXT NOT NULL,
    detail TEXT
);
"""


class Store:
    def __init__(self, path: str):
        self.path = path
        with self._conn() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def save(self, a: Assessment) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO assessments (id, created_at, risk_level, score, data, paypal_order_id) VALUES (?,?,?,?,?,?)",
                (a.id, a.created_at, a.risk_level.value, a.overall_score, a.model_dump_json(), a.paypal_order_id),
            )

    def get(self, assessment_id: str) -> Optional[Assessment]:
        with self._conn() as c:
            row = c.execute("SELECT data FROM assessments WHERE id=?", (assessment_id,)).fetchone()
        return Assessment.model_validate_json(row["data"]) if row else None

    def get_by_order(self, order_id: str) -> Optional[Assessment]:
        with self._conn() as c:
            row = c.execute("SELECT data FROM assessments WHERE paypal_order_id=?", (order_id,)).fetchone()
        return Assessment.model_validate_json(row["data"]) if row else None

    def get_by_capture(self, capture_id: str) -> Optional[Assessment]:
        with self._conn() as c:
            row = c.execute("SELECT data FROM assessments WHERE json_extract(data, '$.capture_id')=?", (capture_id,)).fetchone()
        return Assessment.model_validate_json(row["data"]) if row else None

    def mark_event(self, event_id: str, event_type: str) -> bool:
        """Record a webhook event id. Returns False if it was already processed."""
        with self._conn() as c:
            try:
                c.execute(
                    "INSERT INTO webhook_events (event_id, received_at, event_type) VALUES (?,?,?)",
                    (event_id, datetime.now(timezone.utc).isoformat(), event_type),
                )
            except sqlite3.IntegrityError:
                return False
        return True

    def recent(self, limit: int = 20) -> list[Assessment]:
        with self._conn() as c:
            rows = c.execute("SELECT data FROM assessments ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [Assessment.model_validate_json(r["data"]) for r in rows]

    def log(self, assessment_id: str, event: str, detail: dict | None = None) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO audit_log (assessment_id, at, event, detail) VALUES (?,?,?,?)",
                (assessment_id, datetime.now(timezone.utc).isoformat(), event, json.dumps(detail or {})),
            )

    def audit(self, assessment_id: str) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT at, event, detail FROM audit_log WHERE assessment_id=? ORDER BY seq", (assessment_id,)
            ).fetchall()
        return [{"at": r["at"], "event": r["event"], "detail": json.loads(r["detail"] or "{}")} for r in rows]
