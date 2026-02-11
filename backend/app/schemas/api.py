from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from backend.app.schemas.events import CanonicalEvent, ReplayRequestPayload


T = TypeVar("T")


class ErrorPayload(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    retryable: bool = False


class ResponseEnvelope(BaseModel, Generic[T]):
    request_id: str
    status: str
    data: T | None = None
    error: ErrorPayload | None = None


class CreateRunRequest(BaseModel):
    app_id: str
    environment: str
    source_type: str = "live"
    tags: dict[str, Any] = Field(default_factory=dict)
    retention_class: str = "dev_short"


class CreateRunResponse(BaseModel):
    run_id: str
    trace_id: str
    status: str


class IngestEventRequest(BaseModel):
    idempotency_key: str
    event: CanonicalEvent


class IngestEventResponse(BaseModel):
    event_id: str
    accepted: bool
    validation_warnings: list[str] = Field(default_factory=list)


class RegisterArtifactRequest(BaseModel):
    artifact_type: str
    byte_size: int = Field(ge=0)
    mime_type: str = "application/octet-stream"
    redaction_profile: str = "default"
    content_hash: str | None = None
    content_base64: str | None = None
    content_text: str | None = None
    retention_class: str = "dev_short"
    content_encoding: str = "identity"
    field_policies: dict[str, str] = Field(default_factory=dict)


class RegisterArtifactResponse(BaseModel):
    artifact_hash: str
    upload_required: bool
    upload_target: dict[str, Any]


class FinalizeRunRequest(BaseModel):
    final_status: str
    terminal_event_ref: str | None = None


class FinalizeRunResponse(BaseModel):
    run_id: str
    status: str


class RunSummary(BaseModel):
    run_id: str
    trace_id: str
    app_id: str
    environment: str
    status: str
    source_type: str
    source_run_id: str | None
    started_at_utc: datetime
    ended_at_utc: datetime | None
    retention_class: str


class ListRunsResponse(BaseModel):
    items: list[RunSummary]
    next_page_token: str | None = None


class RunDetailResponse(BaseModel):
    run: RunSummary
    counters: dict[str, int]


class EventView(BaseModel):
    event_id: str
    run_id: str
    step_id: str
    sequence_no: int
    event_type: str
    timestamp_utc: datetime
    determinism_mode: str
    redaction_status: str
    payload: dict[str, Any]


class ListEventsResponse(BaseModel):
    items: list[EventView]
    next_page_token: str | None = None


class ArtifactMetadataResponse(BaseModel):
    artifact_hash: str
    artifact_type: str
    byte_size: int
    mime_type: str
    content_encoding: str
    redaction_profile: str
    status: str
    blocked_reason: str | None
    storage_bucket: str
    storage_object_key: str


class CreateReplaySessionRequest(ReplayRequestPayload):
    pass


class CreateReplaySessionResponse(BaseModel):
    replay_session_id: str
    status: str


class ReplayStatusResponse(BaseModel):
    replay_session_id: str
    status: str
    derived_run_id: str | None = None
    reason_codes: list[str] = Field(default_factory=list)
    failure_reason_code: str | None = None


class CancelReplayResponse(BaseModel):
    status: str
    cancelled_at_utc: datetime
