# 12 Rollout Roadmap

## Purpose
This document defines phased implementation and release sequencing from M0 through M4.

## Roadmap Principles
- Deliver thin vertical slices that are testable end-to-end.
- Prioritize trace correctness and privacy controls before UI polish.
- Keep deterministic replay transparency visible at each milestone.

## Milestone M0: Trace Schema and SDK Capture
Scope:
- Canonical trace schema finalized.
- SDK wrappers for model, retriever, and tool calls.
- Basic ingestion API and metadata persistence.

Entry criteria:
- Architecture and schema docs approved.

Exit criteria:
- Required event types ingest successfully.
- Basic run timeline query works.
- Contract tests for schema and ordering pass.

Primary risks:
- Adapter inconsistencies across frameworks.
Mitigation:
- strict normalization rules and adapter conformance checklist.

## Milestone M1: Artifact Store and Replay Core
Scope:
- Redaction pipeline.
- Content-addressed blob storage.
- Replay orchestrator with exact and cached modes.

Entry criteria:
- M0 completed and stable trace ingestion.

Exit criteria:
- Replay from run start works for deterministic fixture set.
- Artifact dedup verified.
- Privacy policy enforcement verified.

Primary risks:
- Missing artifacts blocking replay.
Mitigation:
- ingestion validation plus retry and pending-artifact diagnostics.

## Milestone M2: Time-Travel UI and Fork/Rerun
Scope:
- Cockpit run detail UI with timeline and step inspector.
- Fork config panel and replay launch.
- Replay status view.

Entry criteria:
- M1 replay API stable.

Exit criteria:
- User can fork from arbitrary step and launch replay from UI.
- Determinism status labels visible in timeline and replay session.

Primary risks:
- UI complexity with large traces.
Mitigation:
- timeline virtualization and incremental loading.

## Milestone M3: Diff Tooling and CI Integration
Scope:
- Diff engine sections (prompt, retrieval, tool, model, output).
- CLI parity for capture/replay/diff.
- Bundle export/import for CI workflows.

Entry criteria:
- M2 functional UI and replay.

Exit criteria:
- CI failed run can be exported and replayed locally.
- Diff report provides causal summary in required sections.

Primary risks:
- Low attribution quality in diff summaries.
Mitigation:
- deterministic attribution heuristic rules with confidence labels.

## Milestone M4: Demo Hardening and Regression Suite
Scope:
- Five curated regression scenarios.
- Performance tuning against capture overhead target.
- Documentation and operability hardening.

Entry criteria:
- M3 end-to-end path stable.

Exit criteria:
- Demonstrable reproducibility target achieved.
- Operational runbooks and alerts validated.
- All acceptance tests pass.

Primary risks:
- Performance regressions under realistic workloads.
Mitigation:
- profiling, worker tuning, and payload optimization.

## Release Management
- Milestone releases use semantic versioning and changelog updates.
- Schema and API compatibility notes included in each release.
- Rollback strategy documented for each service component.

## Decision Gates
Before promoting to next milestone, require:
- test gate pass from `docs/11-test-plan-and-acceptance.md`
- no unresolved critical privacy or data integrity issues
- updated operator runbook entries

## Post-M4 Follow-On Backlog (Out of v1 Scope)
- Multi-tenant authorization model.
- Kubernetes deployment profile.
- Additional framework adapters.
- Advanced attribution using learned causal models.

## Cross-References
- Milestone acceptance tests: `docs/11-test-plan-and-acceptance.md`
- Architecture baseline: `docs/01-architecture-and-components.md`
- Operability requirements: `docs/10-operability-and-sre.md`
