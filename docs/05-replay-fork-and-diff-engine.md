# 05 Replay, Fork, and Diff Engine

## Purpose
This document specifies deterministic replay behavior, fork controls, and run diff generation.

## Replay Objectives
- Reconstruct prior execution accurately enough for root-cause analysis.
- Support replay from run start or from a selected fork step.
- Preserve clear labeling of deterministic confidence per step.

## Replay Inputs
- Source run identifier.
- Fork step identifier (optional, defaults to run start).
- Override profile (prompt/model/retriever/tool modifications).
- Replay mode preferences and policy constraints.

## Replay Orchestration Flow
1. Load source run metadata, steps, events, and required artifacts.
2. Validate source run replay eligibility (required data present, no blocked privacy state).
3. Build execution graph from event lineage.
4. Apply override profile starting at fork step.
5. Execute downstream steps with deterministic policy:
   - exact when recorded output and full signature available.
   - cached when compatible cached output exists.
   - simulated when neither exact nor cached is feasible.
6. Emit replay run events using canonical schema.
7. Finalize replay session with status and diagnostics.

## Fork Model
Fork definitions:
- Logical fork: replay branch derived from immutable source run.
- Source run never mutates.
- Fork includes inherited pre-fork state and modified post-fork policy envelope.

Allowed override categories:
- Prompt template identifier and version.
- Prompt variable overrides.
- Model provider or model ID changes.
- Retriever settings (top_k, filters, embedding profile).
- Tool output simulation payload at selected steps.

Disallowed override categories for v1:
- Structural change to step graph before fork point.
- Deleting source steps.

## Determinism Decision Matrix
For each step type:
- Prompt rendering: deterministic if template and variables are frozen.
- Retrieval: deterministic if candidate list replayed from source artifacts.
- Tool calls: deterministic if cached result available with matching signature.
- Model calls: deterministic if recorded output used; otherwise simulated with explicit label.

## Replay Status Taxonomy
Session statuses:
- `pending`
- `running`
- `completed_exact`
- `completed_mixed`
- `completed_simulated`
- `failed_validation`
- `failed_execution`

Step reason codes include:
- `source_output_reused`
- `cache_hit_signature_match`
- `simulation_operator_override`
- `simulation_policy_fallback`
- `artifact_missing`
- `signature_mismatch`

## Diff Engine Scope
Compares base run and candidate run across:
- Prompt content and template metadata.
- Retrieval candidates (rank movement, additions, removals).
- Tool call signatures and tool outputs.
- Model config and completion outputs.
- Final output and citation changes.

## Diff Computation Rules
- Align steps by lineage mapping and event type.
- Use normalized text comparison for prompt and output diffs.
- Use rank-aware set comparison for retrieval chunks.
- Use signature comparison for tool and model call equivalence.
- Produce summary and detailed sections with confidence scores.

## Causal Attribution Heuristics
Attribution prioritization order:
1. Prompt changes that alter downstream model request.
2. Retrieval candidate changes entering model context.
3. Tool output changes consumed by planner/model.
4. Model configuration differences without upstream input change.

Attribution output:
- primary suspected cause
- supporting changed steps
- confidence level (`high`, `medium`, `low`)

## Failure Modes and Handling
- Missing required source artifact: replay blocked with validation failure.
- Override conflict with policy constraints: reject replay request.
- Downstream execution error: replay marks failed step and emits failure diagnostics.
- Partial diff data: generate report with explicit unavailable sections.

## Performance Targets
- Replay session start under 5 seconds for medium traces.
- Diff generation under 10 seconds for two 10k-step traces with indexed metadata.

## Cross-References
- Event contracts: `docs/02-canonical-trace-spec.md`
- API endpoints for replay and diff: `docs/06-api-contracts.md`
- UI fork interactions: `docs/08-ui-cockpit-spec.md`
