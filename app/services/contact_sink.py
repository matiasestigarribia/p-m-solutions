"""Contact submission persistence — Stage 1.

The ``ContactSink`` protocol is the seam that isolates *where* submissions go
from the request handler. Stage 1 provides two local, no-external-service
implementations:

* ``LoggingSink``  — records the submission to the application log only.
* ``SqliteSink``   — appends to a local SQLite file using the stdlib driver.

Stage 2 (Neon PostgreSQL) will add a third implementation of the same protocol
without changing any caller. Nothing here imports asyncpg, SQLAlchemy, Neon, or
R2, so Stage 1 has no deferred-integration dependency.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional, Protocol

from app.schemas.contact import ContactSubmission

logger = logging.getLogger("pm.contact")

# Persisted columns (the attachment field is inactive in Stage 1 — Stage 2 R2).
_COLUMNS = (
    "full_name", "company", "email", "phone", "location", "solution",
    "project_stage", "need", "priority", "deadline", "contact_preference",
    "best_time",
)


def _payload(submission: ContactSubmission) -> dict:
    data = submission.model_dump()
    return {k: (data.get(k) or "") for k in _COLUMNS}


class ContactSink(Protocol):
    def save(self, submission: ContactSubmission) -> str:
        """Persist a submission and return a reference id."""
        ...


class LoggingSink:
    """Records submissions to the log. Useful for local dev and CI."""

    def save(self, submission: ContactSubmission) -> str:
        ref = uuid.uuid4().hex
        logger.info("contact submission %s: %s", ref, json.dumps(
            _payload(submission), ensure_ascii=False))
        return ref


class SqliteSink:
    """Appends submissions to a local SQLite file (stdlib only)."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        parent = os.path.dirname(os.path.abspath(db_path))
        os.makedirs(parent, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        cols = ",\n".join(f"{c} TEXT" for c in _COLUMNS)
        with self._connect() as conn:
            conn.execute(
                f"""CREATE TABLE IF NOT EXISTS contact_messages (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    {cols}
                )"""
            )

    def save(self, submission: ContactSubmission) -> str:
        ref = uuid.uuid4().hex
        payload = _payload(submission)
        cols = ["id", "created_at", *_COLUMNS]
        placeholders = ",".join("?" for _ in cols)
        values = [ref, datetime.now(timezone.utc).isoformat(),
                  *(payload[c] for c in _COLUMNS)]
        with self._connect() as conn:
            conn.execute(
                f"INSERT INTO contact_messages ({','.join(cols)}) VALUES ({placeholders})",
                values,
            )
        return ref

    def count(self) -> int:
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM contact_messages").fetchone()[0]

    def latest(self) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM contact_messages ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None


def get_contact_sink(settings) -> ContactSink:
    if settings.contact_sink == "sqlite":
        return SqliteSink(settings.contact_db_path)
    return LoggingSink()
