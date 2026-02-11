# 06 API Contracts

## Purpose
This document defines REST API contracts for ingestion, query, replay, diff, and bundle workflows.

## API Conventions
- Base path: `/api/v1`.
- Content type: `application/json`.
- Time format: UTC ISO 8601.
- Identifiers: opaque string IDs.
- Authentication: optional bearer token in local mode, required when enabled.

## Standard Response Envelope
All responses include:
- `request_id`
- `status`
- `data` (on success)
- `error` (on failure)

Error object fields:
- `code`
- `message`
- `details`
- `retryable` (boolean)

## Ingestion Endpoints

### Create Run
- Method: `POST /runs`
- Purpose: initialize run metadata before event ingestion.
- Request fields:
  - `app_id`
  - `environment`
  - `source_type`
  - `tags`
- Response fields:
  - `run_id`
  - `trace_id`
  - `status`

### Ingest Event
- Method: `POST /runs/{run_id}/events`
- Purpose: store one canonical event.
- Request fields:
  - `idempotency_key`
  - `event` (canonical event envelope)
- Response fields:
  - `event_id`
  - `accepted`
  - `validation_warnings`

### Register Artifact
- Method: `POST /artifacts`
- Purpose: register artifact metadata and upload intent.
- Request fields:
  - `artifact_type`
  - `byte_size`
  - `mime_type`
  - `redaction_profile`
  - `content_hash` (optional precomputed)
- Response fields:
  - `artifact_hash`
  - `upload_required`
  - `upload_target`

### Finalize Run
- Method: `POST /runs/{run_id}/finalize`
- Purpose: mark run completed or failed.
- Request fields:
  - `final_status`
  - `terminal_event_ref`
- Response fields:
  - `run_id`
  - `status`

## Query Endpoints

### List Runs
- Method: `GET /runs`
- Filters:
  - `app_id`
  - `environment`
  - `status`
  - `from_utc`
  - `to_utc`
  - `source_type`
- Pagination:
  - `page_size`
  - `page_token`
- Sorting:
  - `started_at_utc` descending default.

### Get Run Detail
- Method: `GET /runs/{run_id}`
- Returns run metadata and summary counters.

### List Run Events
- Method: `GET /runs/{run_id}/events`
- Filters:
  - `event_type`
  - `step_id`
  - `sequence_from`
  - `sequence_to`
- Pagination supported.

### Get Artifact Metadata
- Method: `GET /artifacts/{artifact_hash}`
- Returns metadata and redaction status.

## Replay Endpoints

### Create Replay Session
- Method: `POST /replays`
- Request fields:
  - `source_run_id`
  - `fork_step_id` (optional)
  - `override_profile`
  - `replay_preferences`
- Response fields:
  - `replay_session_id`
  - `status`

### Get Replay Status
- Method: `GET /replays/{replay_session_id}`
- Response fields:
  - `status`
  - `derived_run_id` (when available)
  - `reason_codes`

### Cancel Replay
- Method: `POST /replays/{replay_session_id}/cancel`
- Response fields:
  - `status`
  - `cancelled_at_utc`

## Diff Endpoints

### Create Diff Job
- Method: `POST /diffs`
- Request fields:
  - `base_run_id`
  - `candidate_run_id`
  - `options`
- Response fields:
  - `diff_report_id`
  - `status`

### Get Diff Report
- Method: `GET /diffs/{diff_report_id}`
- Response fields:
  - `summary`
  - `sections` (prompt, retrieval, tool, model, output)
  - `attribution`

## Bundle Endpoints

### Export Bundle
- Method: `POST /bundles/export`
- Request fields:
  - `run_id`
  - `bundle_profile` (`minimal_failure`, `full_debug`)
- Response fields:
  - `bundle_id`
  - `manifest`
  - `download_location`

### Import Bundle
- Method: `POST /bundles/import`
- Request fields:
  - `bundle_location`
  - `import_mode`
- Response fields:
  - `import_id`
  - `run_id`
  - `status`

## Idempotency Rules
- `POST /runs/{run_id}/events` requires idempotency key.
- Duplicate idempotency key returns prior accepted response.
- Artifact registration can also use idempotency key when upload is retried.

## Error Codes (Required Set)
- `VALIDATION_ERROR`
- `AUTH_REQUIRED`
- `AUTH_FORBIDDEN`
- `NOT_FOUND`
- `CONFLICT`
- `RATE_LIMITED`
- `DEPENDENCY_UNAVAILABLE`
- `INTERNAL_ERROR`

## Rate and Payload Limits
- Event payload size and artifact registration limits configurable.
- Server returns explicit limits in validation errors.

## Backward Compatibility
- API version fixed in path.
- Additive fields allowed without version bump.
- Breaking changes require new major path.

## Cross-References
- Trace field definitions: `docs/02-canonical-trace-spec.md`
- Replay and diff semantics: `docs/05-replay-fork-and-diff-engine.md`
- CLI usage: `docs/07-cli-spec.md`
