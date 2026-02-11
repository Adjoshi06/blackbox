# 04 Capture SDK and Adapters

## Purpose
This document defines the SDK capture behavior and adapter interfaces required to instrument LLM applications without changing business logic.

## SDK Responsibilities
- Start and stop run lifecycle.
- Capture step-level events for prompts, retrieval, tools, model calls, validation, and safety.
- Attach deterministic metadata (model params, retriever settings, tool signatures).
- Route artifacts to ingestion API with redaction metadata.
- Maintain event ordering and idempotency keys.

## Integration Modes
- Auto-instrumentation mode: wrapper around supported framework primitives.
- Manual mode: explicit event emission APIs for custom pipelines.
- Hybrid mode: auto hooks with manual overrides for unsupported components.

## Adapter Contracts

### Model Adapter Contract
Required behavior:
- Normalize provider-specific request metadata into canonical model fields.
- Capture pre-call request artifact and post-call response artifact.
- Record latency, token usage, and finish reason.
- Expose call signature hash input for replay caching.

### Retriever Adapter Contract
Required behavior:
- Capture query text and retrieval settings.
- Capture returned candidate list with rank, score, and chunk identity.
- Persist candidate content references and source metadata.

### Tool Adapter Contract
Required behavior:
- Record tool name, version, and argument artifact.
- Record tool status and output artifact.
- Distinguish timeout, error, partial, and success outcomes.

### Planner and Validator Adapter Contract
Required behavior:
- Capture intermediate decision outputs.
- Capture decision rationale references.
- Preserve lineage to prior step inputs.

### Safety Adapter Contract
Required behavior:
- Capture policy decision outcome.
- Capture reason artifact and action taken.

## Run Context Propagation
Each adapter call receives run context containing:
- `run_id`, `trace_id`, current `step_id`, and parent step pointer.
- request-scoped tags (tenant, environment, experiment labels).
- redaction profile reference.

Propagation rules:
- Context must survive async boundaries.
- Child steps inherit run context and set `parent_step_id`.

## Event Emission Rules
- Emit call event before external interaction.
- Emit result event after completion or failure.
- Keep sequence numbers monotonic within run.
- Use deterministic event naming from canonical spec.

## Streaming Capture Policy
For streaming model outputs:
- Capture stream start event metadata.
- Capture chunk summaries optionally for debugging mode.
- Persist final aggregated response as primary artifact for replay and diff.
- Preserve chunk ordering if chunk capture is enabled.

## Error and Retry Semantics
- SDK retries ingestion on transient transport failures.
- Retries must reuse same idempotency key.
- Maximum retry budget configurable by environment.
- After retry exhaustion, SDK writes local spill file if enabled.

## Redaction Hook Interface
Hooks operate in two stages:
- Pre-ingest local hook: quick pattern masking before network transport.
- Server redaction pipeline: authoritative policy enforcement.

Hook outputs:
- redacted payload
- field-level policy decisions
- redaction confidence indicators

Precedence:
- Server policy is final authority.

## CI Capture Mode
CI mode adds:
- deterministic timestamp and environment tagging.
- automatic export of minimal failure bundle on failed run.
- bundle manifest with run metadata, required events, and artifact hashes.

## Performance Budget Requirements
- SDK capture overhead target under 5 percent latency increase.
- Asynchronous artifact upload option for large payloads.
- Configurable sampling disabled by default for failure reproduction reliability.

## Compatibility and Versioning
- SDK must declare supported trace schema major versions.
- Adapter metadata includes adapter version for reproducibility.
- Deprecation windows documented for schema field transitions.

## Cross-References
- Canonical events: `docs/02-canonical-trace-spec.md`
- API ingestion contracts: `docs/06-api-contracts.md`
- Replay and cache behavior: `docs/05-replay-fork-and-diff-engine.md`
