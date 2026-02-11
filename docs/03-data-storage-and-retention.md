# 03 Data Storage and Retention

## Purpose
This document specifies metadata and artifact persistence, retention policies, and storage safety controls for v1.

## Storage Architecture
- Postgres stores run, step, event, replay, diff, and policy metadata.
- MinIO stores immutable artifact blobs addressed by content hash.
- Event records reference artifact hashes rather than duplicating large payloads.

## Logical Postgres Model

### `runs`
Key fields:
- `run_id` (primary key)
- `trace_id`
- `app_id`
- `environment`
- `status`
- `started_at_utc`
- `ended_at_utc`
- `source_type` (`live`, `replay`, `ci_bundle_import`)
- `source_run_id` (nullable)

Indexes:
- `(app_id, started_at_utc desc)`
- `(status, started_at_utc desc)`
- `(trace_id)`

### `steps`
Key fields:
- `step_id` (primary key)
- `run_id` (foreign key)
- `parent_step_id`
- `sequence_no`
- `step_type`
- `started_at_utc`
- `ended_at_utc`
- `determinism_mode`

Unique constraint:
- `(run_id, sequence_no)`

### `events`
Key fields:
- `event_id` (primary key)
- `run_id` (foreign key)
- `step_id` (foreign key)
- `event_type`
- `schema_version`
- `payload_json`
- `redaction_status`
- `created_at_utc`
- `idempotency_key`

Unique constraint:
- `idempotency_key`

### `artifacts`
Key fields:
- `artifact_hash` (primary key)
- `artifact_type`
- `byte_size`
- `mime_type`
- `content_encoding`
- `redaction_profile`
- `storage_bucket`
- `storage_object_key`
- `created_at_utc`
- `retention_class`

### `event_artifacts`
Join table fields:
- `event_id`
- `artifact_hash`
- `reference_role` (for example `rendered_prompt`, `tool_result`)

### `replay_sessions`
Key fields:
- `replay_session_id` (primary key)
- `source_run_id`
- `fork_step_id`
- `override_profile_json`
- `status`
- `started_at_utc`
- `ended_at_utc`
- `failure_reason_code`

### `diff_reports`
Key fields:
- `diff_report_id` (primary key)
- `base_run_id`
- `candidate_run_id`
- `status`
- `summary_json`
- `created_at_utc`

### `audit_log`
Key fields:
- `audit_id` (primary key)
- `actor_id`
- `actor_type`
- `action`
- `target_type`
- `target_id`
- `timestamp_utc`
- `details_json`

## MinIO Object Layout
Bucket strategy:
- Dedicated bucket for artifacts.
- Optional separate bucket for exported CI bundles.

Object key convention:
- Prefix by first bytes of hash for partitioning.
- Full hash as immutable suffix.
- Optional metadata tags for artifact type and retention class.

Immutability rule:
- Blob objects are write-once per hash.
- Metadata updates happen in Postgres, never by blob overwrite.

## Content Addressing and Dedup
Hash policy:
- Compute digest on redacted payload bytes.
- Digest algorithm fixed per schema major version.

Dedup flow:
1. Redact payload.
2. Compute hash.
3. Check existing hash in `artifacts`.
4. If exists, increment reference count logically via join table only.
5. If missing, upload blob and insert artifact metadata.

## Consistency Model
- Event row writes are transactional in Postgres.
- Artifact upload can be eventual relative to event ingestion.
- Events with pending artifact upload carry `artifact_pending` marker until finalized.
- Replay/export must reject unresolved required artifacts.

## Retention Classes
- `dev_short`: 7 days default.
- `ci_medium`: 30 days default.
- `incident_long`: 180 days default.

Retention controls:
- Class assigned per run at ingest or policy evaluation.
- Scheduled cleanup removes expired runs and unreferenced blobs.
- Legal hold flag prevents deletion regardless of retention age.

## Purge Semantics
- Soft delete marker first for auditability window.
- Hard delete after configurable grace period.
- Blob deletion allowed only when no remaining references exist.

## Encryption and Key Management
- Postgres disk encryption via host or managed volume encryption.
- MinIO server-side encryption enabled.
- Keys managed via environment-configured key provider.
- Key rotation schedule documented in operations runbook.

## Backup and Recovery
- Postgres: daily full backup plus periodic incremental snapshots.
- MinIO: bucket replication or snapshot schedule.
- Recovery objective targets:
  - RPO: 24 hours baseline.
  - RTO: 4 hours baseline for single-node setup.

## Capacity and Bloat Controls
- Artifact dedup as primary bloat reduction.
- Compression policy for large text artifacts.
- Configurable truncation for oversized low-value payloads (with hash preserved).
- Dashboard metrics for blob growth rate and retention pressure.

## Cross-References
- Event schema and required references: `docs/02-canonical-trace-spec.md`
- Privacy and redaction controls: `docs/09-security-privacy-compliance.md`
- Operations and backup procedures: `docs/10-operability-and-sre.md`
