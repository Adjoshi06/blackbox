from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.db import models  # noqa: F401
from backend.app.db.session import Base, engine, get_db
from backend.app.modules.artifacts.service import ArtifactService
from backend.app.modules.ingestion.service import create_run, finalize_run, get_run_or_error, ingest_event
from backend.app.modules.ingestion.validation import EventValidationError
from backend.app.modules.query.service import (
    event_to_dict,
    get_artifact_metadata,
    get_run_detail,
    list_events,
    list_runs,
    run_to_summary_dict,
)
from backend.app.modules.replay.service import (
    cancel_replay_session,
    create_replay_session,
    get_replay_session,
)
from backend.app.modules.security.auth import AuthContext, require_auth
from backend.app.schemas.api import (
    CancelReplayResponse,
    CreateReplaySessionRequest,
    CreateReplaySessionResponse,
    CreateRunRequest,
    CreateRunResponse,
    FinalizeRunRequest,
    FinalizeRunResponse,
    IngestEventRequest,
    IngestEventResponse,
    ListEventsResponse,
    ListRunsResponse,
    RegisterArtifactRequest,
    RegisterArtifactResponse,
    ReplayStatusResponse,
    RunDetailResponse,
)
from backend.app.services.artifact_store import build_artifact_store
from backend.app.services.redaction import RedactionEngine
from backend.app.services.responses import error_envelope, request_id, success_envelope


app = FastAPI(title=settings.api_title, version=settings.api_version)
artifact_service = ArtifactService(build_artifact_store(), RedactionEngine())


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.exception_handler(EventValidationError)
async def validation_handler(request: Request, exc: EventValidationError):
    req_id = request_id(request)
    status_code = 400
    if exc.code == "NOT_FOUND":
        status_code = 404
    elif exc.code == "CONFLICT":
        status_code = 409
    return JSONResponse(
        content=jsonable_encoder(
            error_envelope(req_id, exc.code, str(exc), details=exc.details, retryable=False)
        ),
        status_code=status_code,
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    req_id = request_id(request)
    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "INTERNAL_ERROR", "message": str(exc.detail)}
    envelope = error_envelope(
        req_id,
        detail.get("code", "INTERNAL_ERROR"),
        detail.get("message", "Unhandled HTTP exception"),
        details=detail.get("details", {}),
        retryable=detail.get("retryable", False),
    )
    return JSONResponse(content=jsonable_encoder(envelope), status_code=exc.status_code)


@app.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("select 1"))
    return {"status": "ready"}


@app.post("/api/v1/runs")
def api_create_run(
    request: CreateRunRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth),
):
    _ = auth
    run = create_run(db, request)
    payload = CreateRunResponse(run_id=run.run_id, trace_id=run.trace_id, status=run.status)
    return success_envelope(request_id(http_request), payload.model_dump(mode="json"))


@app.post("/api/v1/runs/{run_id}/events")
def api_ingest_event(
    run_id: str,
    request: IngestEventRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth),
):
    _ = auth
    run = get_run_or_error(db, run_id)
    event, accepted, warnings = ingest_event(db, run, request.idempotency_key, request.event)
    payload = IngestEventResponse(event_id=event.event_id, accepted=accepted, validation_warnings=warnings)
    return success_envelope(request_id(http_request), payload.model_dump(mode="json"))


@app.post("/api/v1/artifacts")
def api_register_artifact(
    request: RegisterArtifactRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth),
):
    _ = auth
    response = artifact_service.register_artifact(db, request)
    payload = RegisterArtifactResponse(**response)
    return success_envelope(request_id(http_request), payload.model_dump(mode="json"))


@app.post("/api/v1/runs/{run_id}/finalize")
def api_finalize_run(
    run_id: str,
    request: FinalizeRunRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth),
):
    _ = auth
    run = get_run_or_error(db, run_id)
    run = finalize_run(db, run, request)
    payload = FinalizeRunResponse(run_id=run.run_id, status=run.status)
    return success_envelope(request_id(http_request), payload.model_dump(mode="json"))


@app.get("/api/v1/runs")
def api_list_runs(
    http_request: Request,
    app_id: str | None = Query(default=None),
    environment: str | None = Query(default=None),
    status: str | None = Query(default=None),
    from_utc: str | None = Query(default=None),
    to_utc: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    page_size: int = Query(default=50),
    page_token: str | None = Query(default=None),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth),
):
    _ = auth
    parsed_from = datetime.fromisoformat(from_utc) if from_utc else None
    parsed_to = datetime.fromisoformat(to_utc) if to_utc else None
    rows, next_token = list_runs(
        db,
        app_id=app_id,
        environment=environment,
        status=status,
        from_utc=parsed_from,
        to_utc=parsed_to,
        source_type=source_type,
        page_size=page_size,
        page_token=page_token,
    )
    payload = ListRunsResponse(
        items=[run_to_summary_dict(item) for item in rows],
        next_page_token=next_token,
    )
    return success_envelope(request_id(http_request), payload.model_dump(mode="json"))


@app.get("/api/v1/runs/{run_id}")
def api_get_run(
    run_id: str,
    http_request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth),
):
    _ = auth
    run, counters = get_run_detail(db, run_id)
    payload = RunDetailResponse(run=run_to_summary_dict(run), counters=counters)
    return success_envelope(request_id(http_request), payload.model_dump(mode="json"))


@app.get("/api/v1/runs/{run_id}/events")
def api_list_events(
    run_id: str,
    http_request: Request,
    event_type: str | None = Query(default=None),
    step_id: str | None = Query(default=None),
    sequence_from: int | None = Query(default=None),
    sequence_to: int | None = Query(default=None),
    page_size: int = Query(default=200),
    page_token: str | None = Query(default=None),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth),
):
    _ = auth
    rows, next_token = list_events(
        db,
        run_id=run_id,
        event_type=event_type,
        step_id=step_id,
        sequence_from=sequence_from,
        sequence_to=sequence_to,
        page_size=page_size,
        page_token=page_token,
    )
    payload = ListEventsResponse(items=[event_to_dict(row) for row in rows], next_page_token=next_token)
    return success_envelope(request_id(http_request), payload.model_dump(mode="json"))


@app.get("/api/v1/artifacts/{artifact_hash}")
def api_get_artifact(
    artifact_hash: str,
    http_request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth),
):
    _ = auth
    artifact = get_artifact_metadata(db, artifact_hash)
    payload = {
        "artifact_hash": artifact.artifact_hash,
        "artifact_type": artifact.artifact_type,
        "byte_size": artifact.byte_size,
        "mime_type": artifact.mime_type,
        "content_encoding": artifact.content_encoding,
        "redaction_profile": artifact.redaction_profile,
        "status": artifact.status,
        "blocked_reason": artifact.blocked_reason,
        "storage_bucket": artifact.storage_bucket,
        "storage_object_key": artifact.storage_object_key,
    }
    return success_envelope(request_id(http_request), payload)


@app.post("/api/v1/replays")
def api_create_replay(
    request: CreateReplaySessionRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth),
):
    session = create_replay_session(
        db,
        source_run_id=request.source_run_id,
        fork_step_id=request.fork_step_id,
        override_profile=request.override_profile,
        actor_id=auth.actor_id,
        actor_type=auth.actor_type,
    )
    payload = CreateReplaySessionResponse(replay_session_id=session.replay_session_id, status=session.status)
    return success_envelope(request_id(http_request), payload.model_dump(mode="json"))


@app.get("/api/v1/replays/{replay_session_id}")
def api_get_replay(
    replay_session_id: str,
    http_request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth),
):
    _ = auth
    session = get_replay_session(db, replay_session_id)
    payload = ReplayStatusResponse(
        replay_session_id=session.replay_session_id,
        status=session.status,
        derived_run_id=session.derived_run_id,
        reason_codes=session.reason_codes_json or [],
        failure_reason_code=session.failure_reason_code,
    )
    return success_envelope(request_id(http_request), payload.model_dump(mode="json"))


@app.post("/api/v1/replays/{replay_session_id}/cancel")
def api_cancel_replay(
    replay_session_id: str,
    http_request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth),
):
    _ = auth
    session = cancel_replay_session(db, replay_session_id)
    payload = CancelReplayResponse(
        status=session.status,
        cancelled_at_utc=session.ended_at_utc or datetime.now(timezone.utc),
    )
    return success_envelope(request_id(http_request), payload.model_dump(mode="json"))


@app.post("/api/v1/diffs")
def api_create_diff() -> None:
    raise HTTPException(
        status_code=501,
        detail={
            "code": "NOT_IMPLEMENTED",
            "message": "Diff endpoints are part of M3 scope and are not implemented in this build",
            "details": {},
            "retryable": False,
        },
    )


@app.get("/api/v1/diffs/{diff_report_id}")
def api_get_diff(diff_report_id: str) -> None:
    _ = diff_report_id
    raise HTTPException(
        status_code=501,
        detail={
            "code": "NOT_IMPLEMENTED",
            "message": "Diff endpoints are part of M3 scope and are not implemented in this build",
            "details": {},
            "retryable": False,
        },
    )


@app.post("/api/v1/bundles/export")
def api_bundle_export() -> None:
    raise HTTPException(
        status_code=501,
        detail={
            "code": "NOT_IMPLEMENTED",
            "message": "Bundle workflows are part of M3 scope and are not implemented in this build",
            "details": {},
            "retryable": False,
        },
    )


@app.post("/api/v1/bundles/import")
def api_bundle_import() -> None:
    raise HTTPException(
        status_code=501,
        detail={
            "code": "NOT_IMPLEMENTED",
            "message": "Bundle workflows are part of M3 scope and are not implemented in this build",
            "details": {},
            "retryable": False,
        },
    )
