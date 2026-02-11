from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.models import Event, Run
from backend.app.schemas.events import EVENT_TYPES, REQUIRED_PAYLOAD_FIELDS, CanonicalEvent, ValidationResult


TERMINAL_TYPES = {"run_completed", "run_failed"}


class EventValidationError(ValueError):
    def __init__(self, code: str, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


def validate_event(db: Session, run: Run, event: CanonicalEvent) -> ValidationResult:
    if event.event_type not in EVENT_TYPES:
        raise EventValidationError(
            "VALIDATION_ERROR",
            f"Unsupported event_type '{event.event_type}'",
            {"event_type": event.event_type},
        )

    required = REQUIRED_PAYLOAD_FIELDS.get(event.event_type, set())
    missing = sorted(field for field in required if field not in event.payload)
    if missing:
        raise EventValidationError(
            "VALIDATION_ERROR",
            "Missing required payload fields",
            {"missing_fields": missing, "event_type": event.event_type},
        )

    warnings: list[str] = []

    if event.run_id != run.run_id:
        raise EventValidationError(
            "VALIDATION_ERROR",
            "Event run_id does not match route run_id",
            {"event_run_id": event.run_id, "route_run_id": run.run_id},
        )

    max_sequence = db.execute(
        select(func.max(Event.sequence_no)).where(Event.run_id == run.run_id)
    ).scalar_one()
    if max_sequence is None:
        if event.event_type != "run_started":
            raise EventValidationError(
                "VALIDATION_ERROR",
                "First event in run must be run_started",
                {"event_type": event.event_type},
            )
    else:
        if event.sequence_no <= max_sequence:
            raise EventValidationError(
                "CONFLICT",
                "Event sequence_no must be monotonic and unique",
                {"max_sequence_no": max_sequence, "received": event.sequence_no},
            )

        has_terminal = db.execute(
            select(func.count())
            .select_from(Event)
            .where(Event.run_id == run.run_id, Event.event_type.in_(TERMINAL_TYPES))
        ).scalar_one()
        if has_terminal:
            raise EventValidationError(
                "CONFLICT",
                "Run already has terminal event",
                {"run_id": run.run_id},
            )

    if event.event_type == "model_result":
        model_call_exists = db.execute(
            select(func.count())
            .select_from(Event)
            .where(
                Event.run_id == run.run_id,
                Event.event_type == "model_called",
                Event.step_id == event.step_id,
                Event.sequence_no < event.sequence_no,
            )
        ).scalar_one()
        if model_call_exists == 0:
            raise EventValidationError(
                "VALIDATION_ERROR",
                "model_result requires prior model_called in the same step",
                {"step_id": event.step_id},
            )

    if event.event_type == "tool_result":
        tool_call_exists = db.execute(
            select(func.count())
            .select_from(Event)
            .where(
                Event.run_id == run.run_id,
                Event.event_type == "tool_called",
                Event.step_id == event.step_id,
                Event.sequence_no < event.sequence_no,
            )
        ).scalar_one()
        if tool_call_exists == 0:
            raise EventValidationError(
                "VALIDATION_ERROR",
                "tool_result requires prior tool_called in the same step",
                {"step_id": event.step_id},
            )

    if event.schema_version.split(".")[0] not in {"1", "0"}:
        warnings.append("schema_version_outside_supported_major")

    return ValidationResult(ok=True, warnings=warnings)
