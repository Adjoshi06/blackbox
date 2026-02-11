# 00 System Overview

## Purpose
This document defines the v1 platform scope for the LLM Flight Recorder and Time-Travel Debugger. It gives implementers a shared system view before they build capture, replay, diff, CLI, and UI capabilities.

## Product Intent
The platform is a debugging system for LLM applications (RAG pipelines, multi-step agents, and tool-using assistants). It records every causal step, stores all related artifacts, and enables deterministic replay and controlled re-execution from any step.

## Goals
- Capture complete, privacy-aware run traces.
- Replay failed and successful runs with deterministic behavior where feasible.
- Let users fork from any prior step and rerun with controlled overrides.
- Show causal diffs between original and forked runs.
- Support CI workflows with portable failure bundles.

## Non-Goals
- General APM replacement.
- Petabyte-scale telemetry backend.
- Perfect determinism for all external dependencies.

## Primary Personas
- LLM Platform Engineer: needs reproducible traces for regressions.
- QA and Evaluation Engineer: compares behavior across prompts, retrievers, and models.
- SRE and Incident Responder: diagnoses production incidents caused by LLM decisions.
- Security Engineer: verifies if unsafe or injected content entered the run chain.

## System Context
Inputs:
- User requests and session metadata.
- Model calls, prompt renders, retriever outputs, tool invocations, validators, safety decisions.

Core platform components:
- SDK capture wrappers embedded in target LLM applications.
- Ingestion API for event and artifact registration.
- Artifact storage pipeline with redaction and deduplication.
- Replay and fork orchestrator.
- Diff engine.
- Web cockpit UI.
- CLI for capture, replay, and diff.

Persistence:
- Postgres for metadata and queryable run/step/event state.
- MinIO (S3-compatible) for content-addressed blobs.

## High-Level Capability Map
- Capture: structured event stream and associated artifacts.
- Store: immutable event history plus deduplicated blobs.
- Replay: step graph reconstruction with deterministic mode handling.
- Fork: mutable override envelope starting at any step.
- Diff: compare prompts, retrieval ranks, tool behavior, and outputs.
- CI Integration: export/import failure bundles and replay in local debug environments.

## Core Domain Objects
- Run: one end-to-end execution instance.
- Step: one causal unit inside a run.
- Event: immutable record emitted for a step transition.
- Artifact: large payload content stored by content hash.
- Replay Session: controlled re-execution derived from a source run.
- Diff Report: structured comparison result between two runs.

## End-to-End Happy Path
1. Application starts a run and the SDK emits `run_started`.
2. Each model, retriever, tool, planner, and validator action emits ordered events.
3. Large payloads are redacted, hashed, and persisted as blobs; event payloads reference blob hashes.
4. Run completes and the UI renders a step timeline.
5. User forks from step N, applies overrides (for example model change), and starts replay.
6. Replay engine reconstructs prior context, reuses deterministic artifacts when required, and executes downstream steps.
7. Diff engine computes deltas between original and forked runs.
8. UI presents causal differences and replay confidence labels.

## Quality Attributes
- Reproducibility: maximize repeatability through cached and frozen inputs.
- Observability for debugging: complete step-level visibility.
- Privacy by design: mandatory redaction and policy controls.
- Low overhead: capture target under 5 percent latency overhead.
- Extensibility: adapter model for model/retriever/tool frameworks.

## Deployment Baseline for v1
- Single-node Docker Compose stack.
- Services run as separate containers with internal network isolation.
- Persistent volumes for Postgres and MinIO.
- Intended first for local engineering workflows and CI replay.

## Document Map
- Architecture and components: `docs/01-architecture-and-components.md`
- Canonical event and trace schema: `docs/02-canonical-trace-spec.md`
- Storage and retention: `docs/03-data-storage-and-retention.md`
- SDK and adapters: `docs/04-capture-sdk-and-adapters.md`
- Replay and diff behavior: `docs/05-replay-fork-and-diff-engine.md`
- API contracts: `docs/06-api-contracts.md`
- CLI contracts: `docs/07-cli-spec.md`
- Cockpit UI spec: `docs/08-ui-cockpit-spec.md`
- Security and privacy: `docs/09-security-privacy-compliance.md`
- Operability and SRE: `docs/10-operability-and-sre.md`
- Test and acceptance plan: `docs/11-test-plan-and-acceptance.md`
- Rollout roadmap: `docs/12-rollout-roadmap.md`
