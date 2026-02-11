from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import Artifact, Event, EventArtifact, Run, Step
from backend.app.modules.ingestion.validation import EventValidationError, validate_event
from backend.app.schemas.api import CreateRunRequest, FinalizeRunRequest
from backend.app.schemas.events import CanonicalEvent
from backend.app.services.idempotency import find_existing_event_by_idempotency


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_run(db: Session, request: CreateRunRequest) -> Run:
    run = Run(
        run_id=str(uuid.uuid4()),
        trace_id=str(uuid.uuid4()),
        app_id=request.app_id,
        environment=request.environment,
        status="running",
        source_type=request.source_type,
        tags_json=request.tags,
        retention_class=request.retention_class,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def get_run_or_error(db: Session, run_id: str) -> Run:
    run = db.execute(select(Run).where(Run.run_id == run_id)).scalar_one_or_none()
    if run is None:
        raise EventValidationError("NOT_FOUND", "Run not found", {"run_id": run_id})
    return run


def _upsert_step(db: Session, event: CanonicalEvent) -> Step:
    step = db.execute(select(Step).where(Step.step_id == event.step_id)).scalar_one_or_none()
    if step is None:
        step = Step(
            step_id=event.step_id,
            run_id=event.run_id,
            parent_step_id=event.parent_step_id,
            sequence_no=event.sequence_no,
            step_type=event.event_type,
            determinism_mode=event.determinism_mode,
            started_at_utc=event.timestamp_utc,
        )
        db.add(step)
    else:
        if event.sequence_no < step.sequence_no:
            step.sequence_no = event.sequence_no
        step.ended_at_utc = event.timestamp_utc
        step.determinism_mode = event.determinism_mode
    return step


def ingest_event(db: Session, run: Run, idempotency_key: str, event: CanonicalEvent) -> tuple[Event, bool, list[str]]:
    existing = find_existing_event_by_idempotency(db, idempotency_key)
    if existing is not None:
        return existing, False, []

    validation = validate_event(db, run, event)
    _upsert_step(db, event)

    db_event = Event(
        run_id=event.run_id,
        step_id=event.step_id,
        parent_step_id=event.parent_step_id,
        event_type=event.event_type,
        schema_version=event.schema_version,
        payload_json=event.payload,
        redaction_status=event.redaction_status,
        idempotency_key=idempotency_key,
        sequence_no=event.sequence_no,
        timestamp_utc=event.timestamp_utc,
        actor_type=event.actor_type,
        determinism_mode=event.determinism_mode,
        artifact_pending=False,
    )
    db.add(db_event)
    db.flush()

    for ref in event.artifact_refs:
        artifact = db.execute(
            select(Artifact).where(Artifact.artifact_hash == ref.artifact_hash)
        ).scalar_one_or_none()
        if artifact is None:
            artifact = Artifact(
                artifact_hash=ref.artifact_hash,
                artifact_type=ref.artifact_type,
                byte_size=ref.byte_size,
                mime_type=ref.mime_type,
                content_encoding=ref.content_encoding,
                redaction_profile=ref.redaction_profile,
                storage_bucket="pending",
                storage_object_key="pending",
                status="pending",
            )
            db.add(artifact)
            db_event.artifact_pending = True

        db.add(
            EventArtifact(
                event_id=db_event.event_id,
                artifact_hash=ref.artifact_hash,
                reference_role=ref.artifact_type,
            )
        )

    if event.event_type in {"run_completed", "run_failed"}:
        run.status = "success" if event.event_type == "run_completed" else "failed"
        run.ended_at_utc = _now()

    db.commit()
    db.refresh(db_event)
    return db_event, True, validation.warnings


def finalize_run(db: Session, run: Run, request: FinalizeRunRequest) -> Run:
    if request.final_status not in {"success", "failed"}:
        raise EventValidationError(
            "VALIDATION_ERROR",
            "final_status must be 'success' or 'failed'",
            {"final_status": request.final_status},
        )

    run.status = request.final_status
    run.ended_at_utc = _now()
    db.commit()
    db.refresh(run)
    return run
