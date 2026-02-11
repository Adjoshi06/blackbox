from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from backend.app.db.models import Artifact, Event, Run
from backend.app.modules.ingestion.validation import EventValidationError


def list_runs(
    db: Session,
    app_id: str | None = None,
    environment: str | None = None,
    status: str | None = None,
    from_utc: datetime | None = None,
    to_utc: datetime | None = None,
    source_type: str | None = None,
    page_size: int = 50,
    page_token: str | None = None,
) -> tuple[list[Run], str | None]:
    stmt = select(Run)
    filters = []

    if app_id:
        filters.append(Run.app_id == app_id)
    if environment:
        filters.append(Run.environment == environment)
    if status:
        filters.append(Run.status == status)
    if source_type:
        filters.append(Run.source_type == source_type)
    if from_utc:
        filters.append(Run.started_at_utc >= from_utc)
    if to_utc:
        filters.append(Run.started_at_utc <= to_utc)
    if page_token:
        filters.append(Run.started_at_utc < datetime.fromisoformat(page_token))

    if filters:
        stmt = stmt.where(and_(*filters))

    stmt = stmt.order_by(Run.started_at_utc.desc()).limit(min(max(page_size, 1), 200) + 1)
    rows = list(db.execute(stmt).scalars().all())

    next_page_token = None
    if len(rows) > page_size:
        next_page_token = rows[page_size - 1].started_at_utc.isoformat()
        rows = rows[:page_size]

    return rows, next_page_token


def get_run_detail(db: Session, run_id: str) -> tuple[Run, dict[str, int]]:
    run = db.execute(select(Run).where(Run.run_id == run_id)).scalar_one_or_none()
    if run is None:
        raise EventValidationError("NOT_FOUND", "Run not found", {"run_id": run_id})

    events = db.execute(select(Event.event_type).where(Event.run_id == run_id)).all()
    counters = Counter([evt[0] for evt in events])
    counters["total_events"] = sum(counters.values())
    return run, dict(counters)


def list_events(
    db: Session,
    run_id: str,
    event_type: str | None = None,
    step_id: str | None = None,
    sequence_from: int | None = None,
    sequence_to: int | None = None,
    page_size: int = 200,
    page_token: str | None = None,
) -> tuple[list[Event], str | None]:
    stmt = select(Event).where(Event.run_id == run_id)

    if event_type:
        stmt = stmt.where(Event.event_type == event_type)
    if step_id:
        stmt = stmt.where(Event.step_id == step_id)
    if sequence_from is not None:
        stmt = stmt.where(Event.sequence_no >= sequence_from)
    if sequence_to is not None:
        stmt = stmt.where(Event.sequence_no <= sequence_to)
    if page_token:
        stmt = stmt.where(Event.sequence_no > int(page_token))

    stmt = stmt.order_by(Event.sequence_no.asc()).limit(min(max(page_size, 1), 500) + 1)
    rows = list(db.execute(stmt).scalars().all())

    next_token = None
    if len(rows) > page_size:
        next_token = str(rows[page_size - 1].sequence_no)
        rows = rows[:page_size]

    return rows, next_token


def get_artifact_metadata(db: Session, artifact_hash: str) -> Artifact:
    artifact = db.execute(select(Artifact).where(Artifact.artifact_hash == artifact_hash)).scalar_one_or_none()
    if artifact is None:
        raise EventValidationError(
            "NOT_FOUND",
            "Artifact not found",
            {"artifact_hash": artifact_hash},
        )
    return artifact


def run_to_summary_dict(run: Run) -> dict[str, Any]:
    return {
        "run_id": run.run_id,
        "trace_id": run.trace_id,
        "app_id": run.app_id,
        "environment": run.environment,
        "status": run.status,
        "source_type": run.source_type,
        "source_run_id": run.source_run_id,
        "started_at_utc": run.started_at_utc,
        "ended_at_utc": run.ended_at_utc,
        "retention_class": run.retention_class,
    }


def event_to_dict(event: Event) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "run_id": event.run_id,
        "step_id": event.step_id,
        "sequence_no": event.sequence_no,
        "event_type": event.event_type,
        "timestamp_utc": event.timestamp_utc,
        "determinism_mode": event.determinism_mode,
        "redaction_status": event.redaction_status,
        "payload": event.payload_json,
    }
