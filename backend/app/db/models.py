from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.session import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _uuid_str() -> str:
    return str(uuid.uuid4())


class Run(Base):
    __tablename__ = "runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid_str)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    app_id: Mapped[str] = mapped_column(String(128), index=True)
    environment: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(64), index=True)
    started_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    ended_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), default="live", index=True)
    source_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tags_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    retention_class: Mapped[str] = mapped_column(String(32), default="dev_short")
    legal_hold: Mapped[bool] = mapped_column(Boolean, default=False)


class Step(Base):
    __tablename__ = "steps"

    step_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("runs.run_id"), index=True)
    parent_step_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sequence_no: Mapped[int] = mapped_column(Integer)
    step_type: Mapped[str] = mapped_column(String(64))
    started_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    ended_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    determinism_mode: Mapped[str] = mapped_column(String(32), default="live")

    __table_args__ = (UniqueConstraint("run_id", "sequence_no", name="uq_steps_run_sequence"),)


class Event(Base):
    __tablename__ = "events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid_str)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("runs.run_id"), index=True)
    step_id: Mapped[str] = mapped_column(String(64), ForeignKey("steps.step_id"), index=True)
    parent_step_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    schema_version: Mapped[str] = mapped_column(String(16))
    payload_json: Mapped[dict[str, object]] = mapped_column(JSON)
    redaction_status: Mapped[str] = mapped_column(String(32), default="not_required")
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    idempotency_key: Mapped[str] = mapped_column(String(256), unique=True)
    sequence_no: Mapped[int] = mapped_column(Integer)
    timestamp_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    actor_type: Mapped[str] = mapped_column(String(32), default="sdk")
    determinism_mode: Mapped[str] = mapped_column(String(32), default="live")
    artifact_pending: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (Index("ix_events_run_sequence", "run_id", "sequence_no"),)


class Artifact(Base):
    __tablename__ = "artifacts"

    artifact_hash: Mapped[str] = mapped_column(String(128), primary_key=True)
    artifact_type: Mapped[str] = mapped_column(String(64))
    byte_size: Mapped[int] = mapped_column(Integer)
    mime_type: Mapped[str] = mapped_column(String(128), default="application/octet-stream")
    content_encoding: Mapped[str] = mapped_column(String(64), default="identity")
    redaction_profile: Mapped[str] = mapped_column(String(64), default="default")
    storage_bucket: Mapped[str] = mapped_column(String(128))
    storage_object_key: Mapped[str] = mapped_column(String(256))
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    retention_class: Mapped[str] = mapped_column(String(32), default="dev_short")
    status: Mapped[str] = mapped_column(String(32), default="pending")
    hash_algorithm: Mapped[str] = mapped_column(String(32), default="sha256")
    blocked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class EventArtifact(Base):
    __tablename__ = "event_artifacts"

    event_id: Mapped[str] = mapped_column(String(64), ForeignKey("events.event_id"), primary_key=True)
    artifact_hash: Mapped[str] = mapped_column(
        String(128), ForeignKey("artifacts.artifact_hash"), primary_key=True
    )
    reference_role: Mapped[str] = mapped_column(String(64), primary_key=True)


class ReplaySession(Base):
    __tablename__ = "replay_sessions"

    replay_session_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid_str)
    source_run_id: Mapped[str] = mapped_column(String(64), ForeignKey("runs.run_id"), index=True)
    fork_step_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    override_profile_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(64), default="pending", index=True)
    started_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    ended_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    derived_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason_codes_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)


class DiffReport(Base):
    __tablename__ = "diff_reports"

    diff_report_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid_str)
    base_run_id: Mapped[str] = mapped_column(String(64), index=True)
    candidate_run_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(64), default="pending")
    summary_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class AuditLog(Base):
    __tablename__ = "audit_log"

    audit_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid_str)
    actor_id: Mapped[str] = mapped_column(String(128), default="system")
    actor_type: Mapped[str] = mapped_column(String(64), default="service")
    action: Mapped[str] = mapped_column(String(128), index=True)
    target_type: Mapped[str] = mapped_column(String(64))
    target_id: Mapped[str] = mapped_column(String(64))
    timestamp_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    details_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class Job(Base):
    __tablename__ = "jobs"

    job_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_type: Mapped[str] = mapped_column(String(64), index=True)
    payload_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    retries: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=5)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    available_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
