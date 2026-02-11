# 11 Test Plan and Acceptance

## Purpose
This document defines validation strategy, test scenarios, and acceptance criteria for implementing the platform.

## Test Strategy Overview
Test layers:
- Contract tests for schemas and API behavior.
- Unit tests for redaction, hashing, replay decision logic, and diff algorithms.
- Integration tests across capture, storage, replay, and diff services.
- End-to-end tests through CLI and UI workflows.
- Performance and resilience tests.

## Core Acceptance Mapping to PRD Goals
Goal: complete privacy-aware traces.
- Acceptance: all required event types captured with valid ordering and redaction labels.

Goal: deterministic replay and partial re-execution.
- Acceptance: replay from arbitrary step with mode labels and reproducible outputs in deterministic cases.

Goal: time-travel UI root-cause debugging.
- Acceptance: timeline inspection, fork controls, replay launch, and diff view fully functional.

Goal: run diffing utility.
- Acceptance: prompt/retrieval/tool/model/output differences rendered with attribution summary.

Goal: CI friendliness.
- Acceptance: failed CI runs export minimal bundle and replay locally.

## Detailed Test Matrix

### A) Schema and Validation Tests
- Required field presence for every event type.
- Sequence monotonicity enforcement.
- idempotency duplicate handling.
- schema version compatibility behavior.

### B) Redaction and Privacy Tests
- PII patterns masked according to policy.
- denylist precedence over allowlist.
- hash-only fields never persisted in raw form.
- blocked artifacts prevent replay and export by default.

### C) Storage and Dedup Tests
- identical artifacts map to single hash object.
- event-artifact references preserved across runs.
- retention cleanup removes expired runs and orphaned blobs only.

### D) Replay Tests
- exact replay path with full source artifacts.
- cached replay path with matching signature.
- simulated replay path when external data absent.
- replay failure on missing required artifact.
- fork from middle step with model override.

### E) Diff Tests
- prompt diff detects template and content changes.
- retrieval diff detects rank movement and candidate swaps.
- tool diff detects call signature and output deltas.
- final output diff produced with attribution summary.

### F) API and CLI Tests
- endpoint auth behavior and error codes.
- CLI exit code correctness per scenario.
- CI bundle export/import integrity checks.

### G) UI Workflow Tests
- run list filtering and search.
- timeline navigation for large traces.
- fork configuration validation.
- replay status updates and derived run navigation.
- diff panel rendering and step linking.

### H) Performance and Reliability Tests
- capture overhead under 5 percent in representative workload.
- replay startup and completion targets.
- diff generation latency for large traces.
- retry behavior under transient dependency failures.

## Required End-to-End Scenarios
1. Reproduce a failed RAG answer exactly from stored trace.
2. Fork at retrieval step, change retriever settings, and confirm output change.
3. Fork at model step, change model version, and inspect diff sections.
4. Simulate tool response at step N and validate downstream divergence.
5. Inspect suspected prompt injection from retrieved chunk lineage.
6. Validate redaction on mixed PII payload and ensure export safety.
7. Export failing CI bundle and replay locally via CLI.

## Test Data and Fixtures
- Golden trace fixtures for deterministic replay checks.
- Synthetic sensitive payload suite for redaction testing.
- Large-trace fixture for scalability and UI virtualization checks.

## Quality Gates
Release gate for each milestone requires:
- All critical tests passing.
- No open critical privacy defects.
- Performance thresholds met for target scenarios.
- Documentation contracts unchanged or versioned correctly.

## Exit Criteria by Milestone
- M0: schema + SDK capture contract tests complete.
- M1: artifact dedup + replay deterministic test suite complete.
- M2: UI fork/replay/diff interaction tests complete.
- M3: CLI and CI bundle tests complete.
- M4: regression demo scenarios pass end-to-end.

## Cross-References
- Replay semantics: `docs/05-replay-fork-and-diff-engine.md`
- API and CLI contracts: `docs/06-api-contracts.md`, `docs/07-cli-spec.md`
- Milestone plan: `docs/12-rollout-roadmap.md`
