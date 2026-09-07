from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Job:
    id: str
    payload: dict[str, Any]
    attempts: int
    status: str
    available_at: float
    lease_until: float | None


class Queue:
    """Durable SQLite queue with atomic claims, retries, and leases."""

    def __init__(self, path: str | Path = "jobforge.db", max_attempts: int = 3):
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        self.db = sqlite3.connect(str(path), timeout=30, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.max_attempts = max_attempts
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                available_at REAL NOT NULL,
                lease_until REAL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )"""
        )
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_ready ON jobs(status, available_at)")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_lease ON jobs(status, lease_until)")

    def close(self) -> None:
        self.db.close()

    def enqueue(self, payload: dict[str, Any], delay: float = 0) -> str:
        if not isinstance(payload, dict):
            raise TypeError("payload must be a dictionary")
        now = time.time()
        job_id = uuid.uuid4().hex
        encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        self.db.execute(
            "INSERT INTO jobs VALUES (?, ?, 0, 'queued', ?, NULL, ?, ?)",
            (job_id, encoded, now + max(0, delay), now, now),
        )
        return job_id

    def claim(self, lease_seconds: float = 60) -> Job | None:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be > 0")
        now = time.time()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self._recover_expired(now)
            row = self.db.execute(
                "SELECT * FROM jobs WHERE status='queued' AND available_at <= ? "
                "ORDER BY available_at, created_at LIMIT 1",
                (now,),
            ).fetchone()
            if row is None:
                self.db.execute("COMMIT")
                return None
            lease_until = now + lease_seconds
            attempts = row["attempts"] + 1
            self.db.execute(
                "UPDATE jobs SET status='running', attempts=?, lease_until=?, updated_at=? WHERE id=?",
                (attempts, lease_until, now, row["id"]),
            )
            self.db.execute("COMMIT")
            return self._get(row["id"])
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def complete(self, job_id: str) -> None:
        cur = self.db.execute(
            "UPDATE jobs SET status='completed', lease_until=NULL, updated_at=? "
            "WHERE id=? AND status='running'",
            (time.time(), job_id),
        )
        if cur.rowcount != 1:
            raise KeyError(f"running job not found: {job_id}")

    def fail(self, job_id: str, retry_delay: float = 0) -> None:
        row = self.db.execute("SELECT attempts FROM jobs WHERE id=? AND status='running'", (job_id,)).fetchone()
        if row is None:
            raise KeyError(f"running job not found: {job_id}")
        now = time.time()
        status = "dead" if row["attempts"] >= self.max_attempts else "queued"
        available = now + max(0, retry_delay) if status == "queued" else now
        self.db.execute(
            "UPDATE jobs SET status=?, available_at=?, lease_until=NULL, updated_at=? WHERE id=?",
            (status, available, now, job_id),
        )

    def recover_expired(self) -> int:
        return self._recover_expired(time.time())

    def stats(self) -> dict[str, int]:
        rows = self.db.execute("SELECT status, COUNT(*) AS n FROM jobs GROUP BY status").fetchall()
        result = {"queued": 0, "running": 0, "completed": 0, "dead": 0}
        result.update({row["status"]: row["n"] for row in rows})
        return result

    def _recover_expired(self, now: float) -> int:
        cur = self.db.execute(
            "UPDATE jobs SET status='queued', lease_until=NULL, available_at=?, updated_at=? "
            "WHERE status='running' AND lease_until IS NOT NULL AND lease_until <= ?",
            (now, now, now),
        )
        return cur.rowcount

    def _get(self, job_id: str) -> Job:
        row = self.db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(job_id)
        return Job(
            id=row["id"], payload=json.loads(row["payload"]), attempts=row["attempts"],
            status=row["status"], available_at=row["available_at"], lease_until=row["lease_until"]
        )
