from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from backend.app.db.models import AuditLog, Event, Job, ReplaySession, Run, Step
from backend.app.modules.ingestion.validation import EventValidationError
from backend.app.schemas.events import ReplayOverrideProfile


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_replay_session(
    db: Session,
    source_run_id: str,
    fork_step_id: str | None,
    override_profile: ReplayOverrideProfile,
    actor_id: str,
    actor_type: str,
) -> ReplaySession:
    source_run = db.execute(select(Run).where(Run.run_id == source_run_id)).scalar_one_or_none()
    if source_run is None:
        raise EventValidationError("NOT_FOUND", "source_run_id not found", {"source_run_id": source_run_id})

    if source_run.status not in {"success", "failed"}:
        raise EventValidationError(
            "VALIDATION_ERROR",
            "Source run must be terminal before replay",
            {"status": source_run.status},
        )

    if fork_step_id:
        exists = db.execute(
            select(Step).where(and_(Step.run_id == source_run_id, Step.step_id == fork_step_id))
        ).scalar_one_or_none()
        if exists is None:
            raise EventValidationError(
                "VALIDATION_ERROR",
                "fork_step_id is not part of source run",
                {"fork_step_id": fork_step_id},
            )

    session = ReplaySession(
        replay_session_id=str(uuid.uuid4()),
        source_run_id=source_run_id,
        fork_step_id=fork_step_id,
        override_profile_json=override_profile.model_dump(mode="json"),
        status="pending",
    )
    db.add(session)

    db.add(
        Job(
            job_type="replay_execute",
            payload_json={"replay_session_id": session.replay_session_id},
            status="pending",
        )
    )

    db.add(
        AuditLog(
            actor_id=actor_id,
            actor_type=actor_type,
            action="replay_created",
            target_type="replay_session",
            target_id=session.replay_session_id,
            details_json={
                "source_run_id": source_run_id,
                "fork_step_id": fork_step_id,
            },
        )
    )

    db.commit()
    db.refresh(session)
    return session


def get_replay_session(db: Session, replay_session_id: str) -> ReplaySession:
    session = db.execute(
        select(ReplaySession).where(ReplaySession.replay_session_id == replay_session_id)
    ).scalar_one_or_none()
    if session is None:
        raise EventValidationError(
            "NOT_FOUND",
            "Replay session not found",
            {"replay_session_id": replay_session_id},
        )
    return session


def cancel_replay_session(db: Session, replay_session_id: str) -> ReplaySession:
    session = get_replay_session(db, replay_session_id)
    session.cancel_requested = True
    if session.status in {"pending", "running"}:
        session.status = "failed_execution"
        session.failure_reason_code = "cancel_requested"
        session.ended_at_utc = _now()
    db.commit()
    db.refresh(session)
    return session


def execute_replay_session(db: Session, replay_session_id: str) -> ReplaySession:
    session = get_replay_session(db, replay_session_id)
    if session.status not in {"pending", "running"}:
        return session

    session.status = "running"
    db.commit()

    source_run = db.execute(select(Run).where(Run.run_id == session.source_run_id)).scalar_one()
    source_events = list(
        db.execute(select(Event).where(Event.run_id == source_run.run_id).order_by(Event.sequence_no.asc())).scalars()
    )

    if not source_events:
        session.status = "failed_validation"
        session.failure_reason_code = "source_run_empty"
        session.ended_at_utc = _now()
        db.commit()
        return session

    pending_artifacts = [evt.event_id for evt in source_events if evt.artifact_pending]
    if pending_artifacts:
        session.status = "failed_validation"
        session.failure_reason_code = "artifact_missing"
        session.reason_codes_json = ["artifact_missing"]
        session.ended_at_utc = _now()
        db.commit()
        return session

    override_profile = ReplayOverrideProfile.model_validate(session.override_profile_json)

    derived_run = Run(
        run_id=str(uuid.uuid4()),
        trace_id=str(uuid.uuid4()),
        app_id=source_run.app_id,
        environment=source_run.environment,
        status="running",
        source_type="replay",
        source_run_id=source_run.run_id,
        tags_json={"replay_session_id": session.replay_session_id},
        retention_class=source_run.retention_class,
    )
    db.add(derived_run)
    db.flush()

    fork_sequence = source_events[0].sequence_no
    if session.fork_step_id:
        for event in source_events:
            if event.step_id == session.fork_step_id:
                fork_sequence = event.sequence_no
                break

    step_map: dict[str, str] = {}
    step_first_sequence: dict[str, int] = {}
    for event in source_events:
        step_first_sequence.setdefault(event.step_id, event.sequence_no)

    for original_step_id in step_first_sequence:
        step_map[original_step_id] = str(uuid.uuid5(uuid.uuid4(), f"{derived_run.run_id}:{original_step_id}"))

    reason_codes: list[str] = []
    mode_counts: dict[str, int] = defaultdict(int)

    for index, source_event in enumerate(source_events):
        if session.cancel_requested:
            session.status = "failed_execution"
            session.failure_reason_code = "cancel_requested"
            session.ended_at_utc = _now()
            db.commit()
            return session

        payload = dict(source_event.payload_json)
        payload["source_run_id"] = source_run.run_id
        payload["fork_step_id"] = session.fork_step_id
        payload["override_profile_id"] = session.replay_session_id

        determinism_mode, replay_reason_code = _determinism_for_event(
            source_event,
            fork_sequence,
            override_profile,
            payload,
        )
        payload["replay_reason_code"] = replay_reason_code
        reason_codes.append(replay_reason_code)
        mode_counts[determinism_mode] += 1

        new_step_id = step_map[source_event.step_id]
        new_parent_step_id = step_map.get(source_event.parent_step_id, None)

        step_exists = db.execute(select(Step).where(Step.step_id == new_step_id)).scalar_one_or_none()
        if step_exists is None:
            db.add(
                Step(
                    step_id=new_step_id,
                    run_id=derived_run.run_id,
                    parent_step_id=new_parent_step_id,
                    sequence_no=index,
                    step_type=source_event.event_type,
                    started_at_utc=source_event.timestamp_utc,
                    determinism_mode=determinism_mode,
                )
            )

        replay_event = Event(
            event_id=str(uuid.uuid4()),
            run_id=derived_run.run_id,
            step_id=new_step_id,
            parent_step_id=new_parent_step_id,
            event_type=source_event.event_type,
            schema_version=source_event.schema_version,
            payload_json=payload,
            redaction_status=source_event.redaction_status,
            idempotency_key=f"replay:{session.replay_session_id}:{source_event.event_id}",
            sequence_no=index,
            timestamp_utc=_now(),
            actor_type="replay_engine",
            determinism_mode=determinism_mode,
            artifact_pending=False,
        )
        db.add(replay_event)

    derived_run.status = "success" if source_run.status == "success" else "failed"
    derived_run.ended_at_utc = _now()

    completed_status = _derive_session_status(mode_counts)
    session.status = completed_status
    session.ended_at_utc = _now()
    session.failure_reason_code = None
    session.derived_run_id = derived_run.run_id
    session.reason_codes_json = sorted(set(reason_codes))
    db.commit()
    db.refresh(session)
    return session


def _determinism_for_event(
    source_event: Event,
    fork_sequence: int,
    override_profile: ReplayOverrideProfile,
    payload: dict[str, Any],
) -> tuple[str, str]:
    if source_event.sequence_no < fork_sequence:
        return "exact", "source_output_reused"

    event_type = source_event.event_type

    if event_type == "prompt_rendered" and override_profile.prompt_override:
        if override_profile.prompt_override.template_id:
            payload["prompt_template_id"] = override_profile.prompt_override.template_id
        if override_profile.prompt_override.template_version:
            payload["prompt_template_version"] = override_profile.prompt_override.template_version
        if override_profile.prompt_override.variables:
            payload["prompt_variables_override"] = override_profile.prompt_override.variables
        return "simulated", "simulation_operator_override"

    if event_type in {"model_called", "model_result"} and override_profile.model_override:
        if override_profile.model_override.provider:
            payload["provider"] = override_profile.model_override.provider
        if override_profile.model_override.model_id:
            payload["model_id"] = override_profile.model_override.model_id
        return "simulated", "simulation_operator_override"

    if event_type == "retrieval_executed" and override_profile.retriever_override:
        if override_profile.retriever_override.top_k is not None:
            payload["top_k"] = override_profile.retriever_override.top_k
        if override_profile.retriever_override.filters:
            payload["filters"] = override_profile.retriever_override.filters
        if override_profile.retriever_override.embedding_profile:
            payload["embedding_profile"] = override_profile.retriever_override.embedding_profile
        return "simulated", "simulation_operator_override"

    if (
        event_type == "tool_result"
        and source_event.step_id in override_profile.tool_simulation_overrides
    ):
        payload["result_ref"] = override_profile.tool_simulation_overrides[source_event.step_id]
        return "simulated", "simulation_operator_override"

    if event_type in {
        "tool_called",
        "tool_result",
        "model_called",
        "model_result",
        "retrieval_executed",
    }:
        return "cached", "cache_hit_signature_match"

    return "exact", "source_output_reused"


def _derive_session_status(mode_counts: dict[str, int]) -> str:
    simulated = mode_counts.get("simulated", 0)
    cached = mode_counts.get("cached", 0)
    exact = mode_counts.get("exact", 0)

    if simulated == 0 and cached == 0 and exact > 0:
        return "completed_exact"
    if simulated > 0 and (cached > 0 or exact > 0):
        return "completed_mixed"
    if simulated > 0:
        return "completed_simulated"
    return "completed_mixed"
