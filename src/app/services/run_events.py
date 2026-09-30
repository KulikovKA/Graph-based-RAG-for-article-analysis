"""Atomic durable progress, terminal publication, replay snapshots, and compaction."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from app.services.analysis_run import StageProgress
from app.storage.jobs import JobRepository
from app.storage.models import AnalysisRun, RunEvent, utcnow

MAX_EVENT_BYTES = 65_536
MAX_CHUNK_CHARS = 1024
TERMINAL_EVENTS = {"completed", "failed", "cancelled"}
EVENT_TYPES = {
    "run_started",
    "planning",
    "idea_updated",
    "retrieving",
    "reranking",
    "analyzing",
    "run_requeued",
    "sources_ready",
    "graph_ready",
    "verification",
    "analysis_summary",
    "answer_started",
    "answer_delta",
    "completed",
    "failed",
    "cancelled",
}
EVENT_PAYLOAD_KEYS = {
    "run_started": {"schema_version", "progress"},
    "planning": {"schema_version", "progress"},
    "idea_updated": {"schema_version", "progress", "idea_version_id"},
    "retrieving": {"schema_version", "progress"},
    "reranking": {"schema_version", "progress"},
    "analyzing": {"schema_version", "progress"},
    "run_requeued": {"schema_version", "reason_code", "progress"},
    "sources_ready": {"schema_version", "sources", "coverage"},
    "graph_ready": {"schema_version", "graph_url", "progress"},
    "verification": {"schema_version", "phase", "scope"},
    "analysis_summary": {"schema_version", "public_analysis"},
    "answer_started": {
        "schema_version",
        "presentation_id",
        "renderer_version",
        "text_sha256",
        "chunk_count",
    },
    "answer_delta": {"schema_version", "presentation_id", "chunk_index", "text"},
    "completed": {"schema_version", "run"},
    "failed": {"schema_version", "run"},
    "cancelled": {"schema_version", "run"},
}


@dataclass(frozen=True)
class StoredEvent:
    run_id: UUID
    sequence_no: int
    event_type: str
    payload: dict[str, Any]
    created_at: datetime


class RunEventError(ValueError):
    pass


def run_snapshot(run: AnalysisRun) -> dict[str, Any]:
    evidence_snapshot = run.evidence_snapshot_json or {}
    return {
        "id": str(run.id),
        "status": run.status,
        "stage": run.stage,
        "idea_version_id": str(run.idea_version_id) if run.idea_version_id else None,
        "source_run_id": str(run.source_run_id) if run.source_run_id else None,
        "outcome": run.outcome,
        "answer": run.answer_json,
        "public_analysis": run.public_analysis_json,
        "answer_presentation": run.answer_presentation_json,
        "sources": evidence_snapshot.get("sources", []),
        "progress": run.progress_json or {},
        "coverage": run.coverage_json,
        "graph_url": None,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "error_code": run.error_code,
    }


def _bounded(payload: dict[str, Any]) -> dict[str, Any]:
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_EVENT_BYTES:
        raise RunEventError("event payload exceeds the configured size limit")
    return payload


def add_event(
    session: Session, run: AnalysisRun, event_type: str, payload: dict[str, Any]
) -> RunEvent:
    if event_type not in EVENT_TYPES:
        raise RunEventError("unknown event type")
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise RunEventError("event payload must use schema_version 1")
    expected_keys = EVENT_PAYLOAD_KEYS[event_type]
    if event_type == "verification":
        expected_keys = expected_keys | (
            {"outcome"} if payload.get("phase") == "completed" else {"attempt"}
        )
    if set(payload) != expected_keys:
        raise RunEventError("event payload does not match its typed schema")
    if event_type in TERMINAL_EVENTS:
        if run.status != event_type:
            raise RunEventError("terminal event does not match run status")
        if (
            session.scalar(
                select(RunEvent.sequence_no).where(
                    RunEvent.run_id == run.id, RunEvent.is_terminal.is_(True)
                )
            )
            is not None
        ):
            raise RunEventError("terminal event already exists")
    _bounded(payload)
    run.event_seq_high_water += 1
    event = RunEvent(
        run_id=run.id,
        sequence_no=run.event_seq_high_water,
        event_type=event_type,
        payload_json=payload,
        is_terminal=event_type in TERMINAL_EVENTS,
    )
    session.add(event)
    session.flush()
    return event


def append_progress(
    session: Session,
    run_id: UUID,
    *,
    worker: str,
    token: int,
    update: StageProgress,
) -> bool:
    repo = JobRepository(session)
    run = repo.fenced_run(run_id, worker=worker, token=token)
    if run is None:
        return False
    counts = {
        key: value
        for key, value in {
            "feature_count": update.counts.feature_count,
            "candidate_count": update.counts.candidate_count,
            "selected_document_count": update.counts.selected_document_count,
        }.items()
        if value is not None
    }
    if any(value < 0 for value in counts.values()):
        raise RunEventError("progress counts cannot be negative")
    progress = {
        "schema_version": 1,
        "attempt": update.attempt,
        "stage": update.stage,
        "phase": update.phase,
        "stage_started_at": update.stage_started_at.astimezone(UTC).isoformat(),
        "counts": counts,
    }
    if update.phase == "completed" and update.stage == "verification":
        # Verification is only complete once the result and its projections commit.
        return True
    run.progress_json = progress
    run.stage = update.stage
    event_type = "idea_updated" if update.idea_version_id is not None else update.stage
    if update.stage == "verification":
        payload: dict[str, Any] = {
            "schema_version": 1,
            "phase": "started",
            "scope": "analysis",
            "attempt": update.attempt,
        }
    else:
        payload = {"schema_version": 1, "progress": progress}
    if update.idea_version_id is not None:
        payload["idea_version_id"] = str(update.idea_version_id)
    add_event(session, run, event_type, payload)
    return True


def _answer_chunks(text: str) -> list[str]:
    if not text:
        return [""]
    return [text[index : index + MAX_CHUNK_CHARS] for index in range(0, len(text), MAX_CHUNK_CHARS)]


def result_events(
    *,
    public_analysis: dict[str, Any],
    presentation: dict[str, Any],
    outcome: str,
    run_snapshot: dict[str, Any],
) -> list[tuple[str, dict[str, Any]]]:
    text = presentation.get("text")
    if not isinstance(text, str):
        raise RunEventError("presentation text is missing")
    chunks = _answer_chunks(text)
    if len(chunks) > 128 or len(text.encode("utf-8")) > 65_536:
        raise RunEventError("presentation exceeds the bounded chunk limit")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    presentation_id = hashlib.sha256(
        (str(presentation.get("renderer_version", "")) + text).encode("utf-8")
    ).hexdigest()
    if (
        presentation.get("presentation_id") != presentation_id
        or presentation.get("text_sha256") != digest
        or presentation.get("chunk_count") != len(chunks)
    ):
        raise RunEventError("presentation hash or chunk count mismatch")
    events: list[tuple[str, dict[str, Any]]] = [
        (
            "verification",
            {"schema_version": 1, "phase": "completed", "scope": "result", "outcome": outcome},
        ),
        ("analysis_summary", {"schema_version": 1, "public_analysis": public_analysis}),
        (
            "answer_started",
            {
                "schema_version": 1,
                "presentation_id": presentation["presentation_id"],
                "renderer_version": presentation["renderer_version"],
                "text_sha256": digest,
                "chunk_count": len(chunks),
            },
        ),
    ]
    for index, chunk in enumerate(chunks):
        events.append(
            (
                "answer_delta",
                {
                    "schema_version": 1,
                    "presentation_id": presentation["presentation_id"],
                    "chunk_index": index,
                    "text": chunk,
                },
            )
        )
    events.append(("completed", {"schema_version": 1, "run": run_snapshot}))
    return events


class RunEventsService:
    """Read/replay interface. Callers own the session transaction and auth checks."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def replay(self, run_id: UUID, *, cursor: int | None = None) -> list[StoredEvent]:
        run = self.session.scalar(
            select(AnalysisRun).where(AnalysisRun.id == run_id).with_for_update(read=True)
        )
        if run is None:
            raise LookupError("run not found")
        high_water = run.event_seq_high_water
        cursor = 0 if cursor is None else cursor
        if cursor < 0 or cursor > high_water:
            raise RunEventError("cursor is outside the run event sequence")
        first = self.session.scalar(
            select(RunEvent.sequence_no)
            .where(RunEvent.run_id == run_id)
            .order_by(RunEvent.sequence_no)
            .limit(1)
        )
        compacted = (first is not None and cursor < first - 1) or (
            first is None and cursor < high_water
        )
        if compacted:
            snapshot = {
                "schema_version": 1,
                "run": self.snapshot(run),
                "high_water": high_water,
                "reset": True,
            }
            return [StoredEvent(run.id, high_water, "run_snapshot", snapshot, utcnow())]
        rows = self.session.scalars(
            select(RunEvent)
            .where(RunEvent.run_id == run_id, RunEvent.sequence_no > cursor)
            .order_by(RunEvent.sequence_no)
        )
        return [
            StoredEvent(
                row.run_id, row.sequence_no, row.event_type, row.payload_json, row.created_at
            )
            for row in rows
        ]

    @staticmethod
    def snapshot(run: AnalysisRun) -> dict[str, Any]:
        return run_snapshot(run)

    def compact(self, *, terminal_before: datetime, limit: int = 1000) -> int:
        if limit < 1 or limit > 10_000:
            raise ValueError("invalid compaction limit")
        ids = list(
            self.session.scalars(
                select(AnalysisRun.id)
                .where(
                    AnalysisRun.status.in_(tuple(TERMINAL_EVENTS)),
                    AnalysisRun.completed_at < terminal_before,
                )
                .order_by(AnalysisRun.completed_at, AnalysisRun.id)
                .limit(limit)
            )
        )
        if not ids:
            return 0
        result = cast(
            CursorResult[Any],
            self.session.execute(delete(RunEvent).where(RunEvent.run_id.in_(ids))),
        )
        return int(result.rowcount or 0)


def retention_cutoff(hours: int = 24) -> datetime:
    if hours < 1 or hours > 24 * 30:
        raise ValueError("invalid event retention")
    return utcnow() - timedelta(hours=hours)
