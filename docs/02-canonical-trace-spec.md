# 02 Canonical Trace Specification

## Purpose
This document defines the canonical event and trace contracts for capture, replay, diff, and UI rendering.

## Design Principles
- Immutable events.
- Causal ordering preserved by sequence numbers.
- Separation of metadata and large artifacts.
- Privacy-aware field annotations.
- Schema versioning with backward compatibility.

## Trace Envelope
Every event record includes:
- `schema_version`: semantic version of event contract.
- `trace_id`: stable trace identifier.
- `run_id`: unique run identifier.
- `step_id`: unique step identifier within run.
- `parent_step_id`: previous causal step pointer, nullable for root.
- `sequence_no`: monotonic integer within run.
- `event_type`: event name from allowed set.
- `timestamp_utc`: event creation time in UTC.
- `actor_type`: system component emitting event (`sdk`, `backend`, `replay_engine`).
- `determinism_mode`: `live`, `exact`, `cached`, `simulated`.
- `artifact_refs`: zero or more blob references by hash.
- `redaction_status`: `not_required`, `redacted`, `blocked`, `failed`.
- `payload`: typed event-specific fields.

## Run Lifecycle Event Types

### `run_started`
Required payload:
- `app_id`
- `environment`
- `entrypoint_name`
- `user_session_ref` (if available)
- `input_summary_ref` or inline sanitized summary

### `input_received`
Required payload:
- `input_channels` (chat text, files, api params)
- `input_hash`
- `input_policy_labels`

### `prompt_rendered`
Required payload:
- `prompt_template_id`
- `prompt_template_version`
- `prompt_variables_ref`
- `rendered_prompt_ref`
- `system_message_ref` (optional)

### `retrieval_executed`
Required payload:
- `retriever_id`
- `retriever_version`
- `query_text_ref`
- `top_k`
- `filters`
- `candidate_count`
- `candidate_list_ref`

Candidate list schema:
- `rank`
- `chunk_id`
- `document_id`
- `score`
- `source_uri`
- `content_ref`

### `tool_called`
Required payload:
- `tool_name`
- `tool_version`
- `call_signature_hash`
- `args_ref`
- `timeout_ms`

### `tool_result`
Required payload:
- `tool_name`
- `status` (`success`, `timeout`, `error`, `partial`)
- `result_ref`
- `error_class` (when error)
- `error_message_ref` (sanitized)
- `latency_ms`

### `model_called`
Required payload:
- `provider`
- `model_id`
- `model_api_version`
- `temperature`
- `top_p`
- `max_tokens`
- `seed` (if supported)
- `request_ref`

### `model_result`
Required payload:
- `provider`
- `model_id`
- `finish_reason`
- `token_usage` (prompt, completion, total)
- `response_ref`
- `latency_ms`

### `validator_decision`
Required payload:
- `validator_name`
- `validator_version`
- `decision` (`pass`, `fail`, `warn`)
- `reason_ref`

### `safety_decision`
Required payload:
- `policy_name`
- `policy_version`
- `decision` (`allow`, `block`, `redact`, `escalate`)
- `reason_ref`

### `final_output`
Required payload:
- `output_ref`
- `citations_ref` (optional)
- `response_channel`

### `run_completed`
Required payload:
- `status` (`success`)
- `total_steps`
- `total_latency_ms`

### `run_failed`
Required payload:
- `status` (`failed`)
- `failed_step_id`
- `error_class`
- `error_message_ref`

## Replay-Specific Event Extensions
Replay runs reuse core event types and add:
- `source_run_id`
- `fork_step_id`
- `override_profile_id`
- `replay_reason_code`

## Redaction Field Policies
Each payload field is tagged as one of:
- `raw_allowed`: safe to store directly.
- `redact_required`: must pass redaction pipeline.
- `hash_only`: store digest only.
- `drop`: never stored.

Policy precedence:
1. Explicit denylist field rule.
2. Type-based sensitive default rule.
3. Allowlist override.

## Artifact Reference Contract
Each artifact reference includes:
- `artifact_hash`
- `artifact_type`
- `byte_size`
- `content_encoding`
- `mime_type`
- `redaction_profile`

## Event Ordering and Causality Rules
- `run_started` must be first event of each run.
- `run_completed` or `run_failed` must be terminal event.
- `model_result` requires prior matching `model_called` in same run and step lineage.
- `tool_result` requires prior matching `tool_called`.
- Sequence numbers must be unique and monotonic per run.

## Validation Rules
- Required fields enforced by event type.
- Unknown fields allowed only when `schema_version` minor version supports extensions.
- Missing artifact for required refs marks event invalid unless explicitly optional.

## Versioning and Compatibility
- Major version change for breaking field removals or semantic shifts.
- Minor version change for additive optional fields.
- Patch version for clarifications and non-structural constraints.
- Backend must support at least current major and previous major for read compatibility.

## Invariants Required by Other Components
- Replay engine depends on complete call signatures for model/retriever/tool events.
- Diff engine depends on stable `step_id` lineage and normalized payload references.
- UI timeline depends on strict `sequence_no` and event type taxonomy.

## Cross-References
- Storage mapping: `docs/03-data-storage-and-retention.md`
- Replay semantics: `docs/05-replay-fork-and-diff-engine.md`
- API payload contracts: `docs/06-api-contracts.md`
