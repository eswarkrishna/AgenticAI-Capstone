"""SQLite tracking table and append-only recruiter override log."""

from __future__ import annotations

import csv
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from resume_screener.config import Settings
from resume_screener.paths import OVERRIDES_PATH
from resume_screener.schemas import MatchLabel, TrackingRecord

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS tracking (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    resume_filename TEXT NOT NULL,
    jd_title TEXT NOT NULL,
    candidate_profile_json TEXT NOT NULL,
    role_profile_json TEXT NOT NULL,
    retrieved_chunk_ids TEXT NOT NULL,
    scorecard_json TEXT NOT NULL,
    predicted_label TEXT,
    final_label TEXT,
    confidence REAL NOT NULL,
    needs_human_review INTEGER NOT NULL,
    overridden INTEGER NOT NULL DEFAULT 0,
    recruiter_notes TEXT NOT NULL DEFAULT '',
    thread_id TEXT NOT NULL,
    error TEXT
);
"""

_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_tracking_thread ON tracking(thread_id);",
    "CREATE INDEX IF NOT EXISTS idx_tracking_pending ON tracking(needs_human_review);",
)


def _default_sqlite_path() -> Path:
    return Path(Settings().sqlite_path)


def _default_overrides_path() -> Path:
    return OVERRIDES_PATH


@contextmanager
def _connect(sqlite_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    path = Path(sqlite_path or _default_sqlite_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(_CREATE_SQL)
        for stmt in _INDEX_SQL:
            conn.execute(stmt)
        yield conn
        conn.commit()
    finally:
        conn.close()


def _dump_json(value: Any) -> str:
    return json.dumps(value, default=str)


def _load_json(raw: str | None, default: Any) -> Any:
    if not raw:
        return default
    return json.loads(raw)


def _parse_dt(raw: str) -> datetime:
    text = raw.replace("Z", "+00:00")
    value = datetime.fromisoformat(text)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _label(raw: str | None) -> MatchLabel | None:
    if raw is None or raw == "":
        return None
    return MatchLabel(raw)


def _row_to_record(row: sqlite3.Row) -> TrackingRecord:
    return TrackingRecord(
        id=row["id"],
        created_at=_parse_dt(row["created_at"]),
        resume_filename=row["resume_filename"],
        jd_title=row["jd_title"],
        candidate_profile_json=_load_json(row["candidate_profile_json"], {}),
        role_profile_json=_load_json(row["role_profile_json"], {}),
        retrieved_chunk_ids=_load_json(row["retrieved_chunk_ids"], []),
        scorecard_json=_load_json(row["scorecard_json"], {}),
        predicted_label=_label(row["predicted_label"]),
        final_label=_label(row["final_label"]),
        confidence=float(row["confidence"] or 0.0),
        needs_human_review=bool(row["needs_human_review"]),
        overridden=bool(row["overridden"]),
        recruiter_notes=row["recruiter_notes"] or "",
        thread_id=row["thread_id"],
        error=row["error"],
    )


def insert_run(record: TrackingRecord, sqlite_path: Path | None = None) -> TrackingRecord:
    """Insert or replace a tracking row. Every screening run must land here."""
    with _connect(sqlite_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO tracking (
                id, created_at, resume_filename, jd_title,
                candidate_profile_json, role_profile_json, retrieved_chunk_ids,
                scorecard_json, predicted_label, final_label, confidence,
                needs_human_review, overridden, recruiter_notes, thread_id, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.id,
                record.created_at.isoformat(),
                record.resume_filename,
                record.jd_title,
                _dump_json(record.candidate_profile_json),
                _dump_json(record.role_profile_json),
                _dump_json(record.retrieved_chunk_ids),
                _dump_json(record.scorecard_json),
                None if record.predicted_label is None else record.predicted_label.value,
                None if record.final_label is None else record.final_label.value,
                record.confidence,
                int(record.needs_human_review),
                int(record.overridden),
                record.recruiter_notes,
                record.thread_id,
                record.error,
            ),
        )
    return record


def get_run(tracking_id: str, sqlite_path: Path | None = None) -> TrackingRecord | None:
    with _connect(sqlite_path) as conn:
        row = conn.execute(
            "SELECT * FROM tracking WHERE id = ?", (tracking_id,)
        ).fetchone()
    return _row_to_record(row) if row else None


def get_run_by_thread(thread_id: str, sqlite_path: Path | None = None) -> TrackingRecord | None:
    with _connect(sqlite_path) as conn:
        row = conn.execute(
            "SELECT * FROM tracking WHERE thread_id = ? ORDER BY created_at DESC LIMIT 1",
            (thread_id,),
        ).fetchone()
    return _row_to_record(row) if row else None


def finalize_disposition(
    tracking_id: str,
    final_label: MatchLabel,
    notes: str = "",
    sqlite_path: Path | None = None,
) -> TrackingRecord:
    """Set final label after HITL. `overridden` is true when it differs from predicted."""
    current = get_run(tracking_id, sqlite_path=sqlite_path)
    if current is None:
        raise KeyError(f"no tracking row for {tracking_id}")
    overridden = current.predicted_label is not None and final_label != current.predicted_label
    with _connect(sqlite_path) as conn:
        conn.execute(
            """
            UPDATE tracking
            SET final_label = ?, overridden = ?, recruiter_notes = ?, needs_human_review = 0
            WHERE id = ?
            """,
            (final_label.value, int(overridden), notes, tracking_id),
        )
    updated = get_run(tracking_id, sqlite_path=sqlite_path)
    assert updated is not None
    return updated


def list_pending_review(sqlite_path: Path | None = None) -> list[TrackingRecord]:
    with _connect(sqlite_path) as conn:
        rows = conn.execute(
            """
            SELECT * FROM tracking
            WHERE needs_human_review = 1
            ORDER BY created_at ASC
            """
        ).fetchall()
    return [_row_to_record(row) for row in rows]


def list_all(sqlite_path: Path | None = None) -> list[TrackingRecord]:
    with _connect(sqlite_path) as conn:
        rows = conn.execute(
            "SELECT * FROM tracking ORDER BY created_at DESC"
        ).fetchall()
    return [_row_to_record(row) for row in rows]


def append_override(
    record: TrackingRecord,
    notes: str = "",
    overrides_path: Path | None = None,
) -> None:
    """Append one recruiter decision to the JSONL override log."""
    path = Path(overrides_path or _default_overrides_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "tracking_id": record.id,
        "thread_id": record.thread_id,
        "predicted_label": None
        if record.predicted_label is None
        else record.predicted_label.value,
        "final_label": None if record.final_label is None else record.final_label.value,
        "overridden": record.overridden,
        "notes": notes or record.recruiter_notes,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")


def export_csv(destination: Path, sqlite_path: Path | None = None) -> Path:
    """Write all tracking rows. Filenames are allowed; no demographic columns exist."""
    dest = Path(destination)
    dest.parent.mkdir(parents=True, exist_ok=True)
    rows = list_all(sqlite_path=sqlite_path)
    fieldnames = list(TrackingRecord.model_fields)
    with dest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in rows:
            dumped = record.model_dump(mode="json")
            dumped["created_at"] = record.created_at.isoformat()
            dumped["candidate_profile_json"] = json.dumps(record.candidate_profile_json)
            dumped["role_profile_json"] = json.dumps(record.role_profile_json)
            dumped["retrieved_chunk_ids"] = json.dumps(record.retrieved_chunk_ids)
            dumped["scorecard_json"] = json.dumps(record.scorecard_json)
            writer.writerow(dumped)
    return dest
