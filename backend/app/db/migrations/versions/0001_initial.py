"""initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-02-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "runs",
        sa.Column("run_id", sa.String(length=64), primary_key=True),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("app_id", sa.String(length=128), nullable=False),
        sa.Column("environment", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("started_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_run_id", sa.String(length=64), nullable=True),
        sa.Column("tags_json", sa.JSON(), nullable=False),
        sa.Column("retention_class", sa.String(length=32), nullable=False),
        sa.Column("legal_hold", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_runs_app_started", "runs", ["app_id", "started_at_utc"])
    op.create_index("ix_runs_status_started", "runs", ["status", "started_at_utc"])
    op.create_index("ix_runs_trace_id", "runs", ["trace_id"])

    op.create_table(
        "steps",
        sa.Column("step_id", sa.String(length=64), primary_key=True),
        sa.Column("run_id", sa.String(length=64), sa.ForeignKey("runs.run_id"), nullable=False),
        sa.Column("parent_step_id", sa.String(length=64), nullable=True),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("step_type", sa.String(length=64), nullable=False),
        sa.Column("started_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("determinism_mode", sa.String(length=32), nullable=False),
        sa.UniqueConstraint("run_id", "sequence_no", name="uq_steps_run_sequence"),
    )
    op.create_index("ix_steps_run_id", "steps", ["run_id"])

    op.create_table(
        "events",
        sa.Column("event_id", sa.String(length=64), primary_key=True),
        sa.Column("run_id", sa.String(length=64), sa.ForeignKey("runs.run_id"), nullable=False),
        sa.Column("step_id", sa.String(length=64), sa.ForeignKey("steps.step_id"), nullable=False),
        sa.Column("parent_step_id", sa.String(length=64), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=16), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("redaction_status", sa.String(length=32), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=256), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("timestamp_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("determinism_mode", sa.String(length=32), nullable=False),
        sa.Column("artifact_pending", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_events_idempotency"),
    )
    op.create_index("ix_events_run_id", "events", ["run_id"])
    op.create_index("ix_events_step_id", "events", ["step_id"])
    op.create_index("ix_events_event_type", "events", ["event_type"])
    op.create_index("ix_events_run_sequence", "events", ["run_id", "sequence_no"])

    op.create_table(
        "artifacts",
        sa.Column("artifact_hash", sa.String(length=128), primary_key=True),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("content_encoding", sa.String(length=64), nullable=False),
        sa.Column("redaction_profile", sa.String(length=64), nullable=False),
        sa.Column("storage_bucket", sa.String(length=128), nullable=False),
        sa.Column("storage_object_key", sa.String(length=256), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retention_class", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("hash_algorithm", sa.String(length=32), nullable=False),
        sa.Column("blocked_reason", sa.Text(), nullable=True),
    )

    op.create_table(
        "event_artifacts",
        sa.Column("event_id", sa.String(length=64), sa.ForeignKey("events.event_id"), primary_key=True),
        sa.Column(
            "artifact_hash",
            sa.String(length=128),
            sa.ForeignKey("artifacts.artifact_hash"),
            primary_key=True,
        ),
        sa.Column("reference_role", sa.String(length=64), primary_key=True),
    )

    op.create_table(
        "replay_sessions",
        sa.Column("replay_session_id", sa.String(length=64), primary_key=True),
        sa.Column("source_run_id", sa.String(length=64), sa.ForeignKey("runs.run_id"), nullable=False),
        sa.Column("fork_step_id", sa.String(length=64), nullable=True),
        sa.Column("override_profile_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("started_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason_code", sa.String(length=64), nullable=True),
        sa.Column("derived_run_id", sa.String(length=64), nullable=True),
        sa.Column("reason_codes_json", sa.JSON(), nullable=False),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_replay_sessions_source_run", "replay_sessions", ["source_run_id"])
    op.create_index("ix_replay_sessions_status", "replay_sessions", ["status"])

    op.create_table(
        "diff_reports",
        sa.Column("diff_report_id", sa.String(length=64), primary_key=True),
        sa.Column("base_run_id", sa.String(length=64), nullable=False),
        sa.Column("candidate_run_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "audit_log",
        sa.Column("audit_id", sa.String(length=64), primary_key=True),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("actor_type", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=False),
        sa.Column("timestamp_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=False),
    )
    op.create_index("ix_audit_action", "audit_log", ["action"])

    op.create_table(
        "jobs",
        sa.Column("job_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("retries", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("available_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at_utc", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_jobs_job_type", "jobs", ["job_type"])
    op.create_index("ix_jobs_status", "jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_index("ix_jobs_job_type", table_name="jobs")
    op.drop_table("jobs")

    op.drop_index("ix_audit_action", table_name="audit_log")
    op.drop_table("audit_log")

    op.drop_table("diff_reports")

    op.drop_index("ix_replay_sessions_status", table_name="replay_sessions")
    op.drop_index("ix_replay_sessions_source_run", table_name="replay_sessions")
    op.drop_table("replay_sessions")

    op.drop_table("event_artifacts")
    op.drop_table("artifacts")

    op.drop_index("ix_events_run_sequence", table_name="events")
    op.drop_index("ix_events_event_type", table_name="events")
    op.drop_index("ix_events_step_id", table_name="events")
    op.drop_index("ix_events_run_id", table_name="events")
    op.drop_table("events")

    op.drop_index("ix_steps_run_id", table_name="steps")
    op.drop_table("steps")

    op.drop_index("ix_runs_trace_id", table_name="runs")
    op.drop_index("ix_runs_status_started", table_name="runs")
    op.drop_index("ix_runs_app_started", table_name="runs")
    op.drop_table("runs")
