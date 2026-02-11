from backend.app.db.models import Run
from backend.app.modules.ingestion.validation import EventValidationError, validate_event
from backend.app.schemas.events import CanonicalEvent


def build_event(event_type: str, sequence_no: int = 0) -> CanonicalEvent:
    return CanonicalEvent(
        schema_version="1.0.0",
        trace_id="trace-1",
        run_id="run-1",
        step_id="step-1",
        parent_step_id=None,
        sequence_no=sequence_no,
        event_type=event_type,
        timestamp_utc="2026-02-11T00:00:00Z",
        actor_type="sdk",
        determinism_mode="live",
        artifact_refs=[],
        redaction_status="not_required",
        payload={
            "app_id": "demo",
            "environment": "test",
            "entrypoint_name": "unit",
        },
    )


def test_first_event_must_be_run_started(client) -> None:
    from backend.app.db.session import SessionLocal

    with SessionLocal() as db:
        run = Run(
            run_id="run-1",
            trace_id="trace-1",
            app_id="demo",
            environment="test",
            status="running",
            source_type="live",
        )
        db.add(run)
        db.commit()

        event = build_event("model_called")
        event.payload = {
            "provider": "openai",
            "model_id": "gpt",
            "model_api_version": "v1",
            "temperature": 0.0,
            "top_p": 1.0,
            "max_tokens": 32,
            "request_ref": "hash",
        }

        try:
            validate_event(db, run, event)
            raised = False
        except EventValidationError:
            raised = True

        assert raised
