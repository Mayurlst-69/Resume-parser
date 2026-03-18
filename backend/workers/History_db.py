import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "History_db"


def _get_conn():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if not exist."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS batches (
                batch_id    TEXT PRIMARY KEY,
                created_at  TEXT NOT NULL,
                total_files INTEGER NOT NULL,
                done_files  INTEGER NOT NULL,
                flagged     INTEGER NOT NULL DEFAULT 0,
                failed      INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS batch_jobs (
                job_id       TEXT PRIMARY KEY,
                batch_id     TEXT NOT NULL,
                filename     TEXT NOT NULL,
                status       TEXT NOT NULL,
                parse_method TEXT,
                file_size_kb REAL,
                name         TEXT,
                position     TEXT,
                phone        TEXT,
                email        TEXT,
                confidence   REAL,
                error        TEXT,
                FOREIGN KEY (batch_id) REFERENCES batches(batch_id)
            )
        """)
        conn.commit()


def save_batch(batch_id: str, jobs: list):
    """Persist a completed batch and all its jobs to SQLite."""
    init_db()

    from api.models import JobStatus

    total = len(jobs)
    done = sum(1 for j in jobs if j.status == JobStatus.done)
    flagged = sum(1 for j in jobs if j.status == JobStatus.low_confidence)
    failed = sum(1 for j in jobs if j.status == JobStatus.failed)

    with _get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO batches
                (batch_id, created_at, total_files, done_files, flagged, failed)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            batch_id,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            total, done, flagged, failed,
        ))

        for job in jobs:
            r = job.result
            conn.execute("""
                INSERT OR REPLACE INTO batch_jobs
                    (job_id, batch_id, filename, status, parse_method,
                    file_size_kb, name, position, phone, email, confidence, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.job_id, batch_id, job.filename, job.status.value,
                job.parse_method, job.file_size_kb,
                r.name if r else None,
                r.position if r else None,
                r.phone if r else None,
                r.email if r else None,
                r.confidence if r else None,
                job.error,
            ))
        conn.commit()


def list_batches() -> list[dict]:
    """Return all batches sorted newest first."""
    init_db()
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM batches ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_batch_jobs(batch_id: str) -> list[dict]:
    """Return all jobs for a batch."""
    init_db()
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM batch_jobs WHERE batch_id = ?", (batch_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def delete_batch(batch_id: str):
    """Delete a batch and all its jobs."""
    init_db()
    with _get_conn() as conn:
        conn.execute("DELETE FROM batch_jobs WHERE batch_id = ?", (batch_id,))
        conn.execute("DELETE FROM batches WHERE batch_id = ?", (batch_id,))
        conn.commit()