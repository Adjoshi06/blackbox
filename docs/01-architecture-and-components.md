# 01 Architecture and Components

## Scope
This document defines the runtime architecture for v1 using Python and FastAPI, Postgres, and MinIO in a single-node Docker Compose environment.

## Architecture Style
- Modular monolith service boundary for v1 backend API with well-defined internal modules.
- Background worker process for async-heavy tasks (artifact processing, replay orchestration, diff computation).
- Separate frontend web client consuming backend APIs.
- CLI as an external client that uses the same backend interfaces.

## Component Inventory

### 1) SDK Capture Layer (Client-Side)
Responsibilities:
- Intercept model, retriever, tool, planner, validator, and safety calls.
- Emit ordered events to ingestion API.
- Stream large payload metadata and artifact references.
- Apply local pre-redaction hooks before transport.

Failure boundary:
- Capture failures must not crash host application by default.
- Fail-open or fail-closed behavior configurable per environment.

### 2) Ingestion API (FastAPI)
Responsibilities:
- Authenticate requests (optional token gate in local mode).
- Validate event schema and sequence constraints.
- Persist event metadata to Postgres.
- Register artifacts for asynchronous processing.
- Provide idempotent write behavior.

Failure boundary:
- Reject malformed events with deterministic error codes.
- Preserve partial run history with explicit run status.

### 3) Artifact Service
Responsibilities:
- Run redaction pipeline.
- Compute content hash and deduplicate blob storage.
- Persist metadata pointers between events and blobs.
- Store in MinIO with immutable object keys.

Failure boundary:
- Redaction failures mark run as privacy-risk and block replay/export unless override policy allows.

### 4) Replay Orchestrator
Responsibilities:
- Reconstruct execution graph from source run.
- Enforce replay mode policy (exact, cached, simulated).
- Execute forked downstream steps from selected fork point.
- Emit replay events using same canonical schema.

Failure boundary:
- Replay session can fail independently without mutating source run.

### 5) Diff Engine
Responsibilities:
- Compare source and candidate run events and artifacts.
- Compute prompt, retrieval, tool, model, and output deltas.
- Generate structured diff report with confidence and attribution hints.

Failure boundary:
- Partial diff output allowed with explicit missing sections.

### 6) Query and UI Backend Module
Responsibilities:
- Serve run listing, timeline details, replay session views, and diff reports.
- Aggregate event + artifact metadata for UI panels.

### 7) Cockpit UI (React)
Responsibilities:
- Timeline exploration.
- Step detail inspection.
- Fork configuration and replay launch.
- Diff visualization and incident replay workflows.

### 8) CLI
Responsibilities:
- Capture wrapper for command execution.
- Replay bundle execution.
- Run-to-run diff invocation.

## Runtime Topology (v1)
- `api` container: FastAPI application.
- `worker` container: async jobs.
- `web` container: React app.
- `postgres` container: metadata persistence.
- `minio` container: blob storage.
- Optional `mc` or bootstrap container: MinIO bucket initialization.

## Internal Module Boundaries in Backend
- `ingestion`: write path for runs, steps, events.
- `artifacts`: redaction, hashing, blob registration.
- `replay`: replay graph, fork logic, execution manager.
- `diff`: run comparator and report model.
- `query`: optimized read models for UI/CLI.
- `security`: policy enforcement for redaction and access checks.

## Sync vs Async Work Split
Synchronous API path:
- Run creation and event metadata validation.
- Minimal metadata persistence.

Asynchronous worker path:
- Large artifact ingestion and redaction.
- Replay execution.
- Diff computation for large traces.

Reasoning:
- Keeps ingestion latency low and supports capture overhead target.

## Determinism Modes
- Exact: downstream steps replay with frozen inputs and recorded outputs; no external calls.
- Cached: external call replaced by cached prior output validated against call signature.
- Simulated: external output unavailable; replay uses operator-supplied or policy-defined simulation payload.

All replayed steps carry mode labels in event metadata and UI.

## Idempotency and Ordering
- Every ingest request includes idempotency key derived from `run_id + step_id + event_type + sequence_no`.
- Events within a run must be strictly ordered by sequence number.
- Late arrivals are accepted only if sequence gaps are resolvable and validation passes.

## Failure Handling Model
- Validation errors: reject event, record structured error response.
- Storage transient errors: retry with exponential backoff; preserve idempotency.
- Irrecoverable artifact errors: mark event artifact status as failed and flag run health.
- Replay job errors: mark replay session failed with reason code and failed step pointer.

## Performance Targets
- Ingestion overhead target: less than 5 percent incremental latency relative to uninstrumented run.
- UI run detail load target: timeline summary within 2 seconds for 10k-step runs.
- Replay start time target: under 5 seconds from user trigger for medium traces.

## Extensibility Strategy
- Adapter contracts isolate integration differences among model providers and frameworks.
- Schema versioning enables additive event payload growth.
- Replay engine plug points allow future deterministic plugins for new tool types.

## Dependencies and Rationale
- FastAPI: rapid API development and rich validation ecosystem.
- Postgres: strong relational queries for run, step, and diff exploration.
- MinIO/S3: scalable blob storage and local parity with production-like environments.
- React: interactive timeline and fork controls.

## Cross-References
- Trace schema: `docs/02-canonical-trace-spec.md`
- Storage model: `docs/03-data-storage-and-retention.md`
- Replay mechanics: `docs/05-replay-fork-and-diff-engine.md`
- API contracts: `docs/06-api-contracts.md`
