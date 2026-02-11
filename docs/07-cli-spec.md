# 07 CLI Specification

## Purpose
This document defines the command-line interface for capture, replay, and diff workflows, including CI usage behavior.

## CLI Design Principles
- Same core semantics as backend APIs.
- Human-readable output by default.
- Machine-readable output option for CI automation.
- Stable exit codes for pipeline gating.

## Global Behavior
- Binary name: `trace`.
- Default API target: local backend endpoint.
- Optional authentication token via environment variable.
- Output formats: `text`, `json`.

Global flags:
- `--api-url`
- `--auth-token`
- `--output`
- `--timeout`
- `--verbose`

## Command: Capture
Syntax:
- `trace capture --run <command>`

Required behavior:
- Launches target command with capture context.
- Starts run record before command execution.
- Collects emitted events and artifacts during command lifetime.
- Finalizes run with success/failure based on command exit status.

Key flags:
- `--app-id`
- `--env`
- `--bundle-on-fail` (CI-friendly)
- `--retention-class`

Outputs:
- `run_id`
- `trace_id`
- command exit code mirror

## Command: Replay
Syntax:
- `trace replay <bundle_or_run_ref>`

Required behavior:
- Resolves source run from local bundle or remote run reference.
- Applies optional fork settings.
- Starts replay session and streams status until terminal state.

Key flags:
- `--fork-step`
- `--override-profile`
- `--wait`
- `--fail-on-simulated`

Outputs:
- `replay_session_id`
- derived `run_id` when successful
- terminal replay status and reason codes

## Command: Diff
Syntax:
- `trace diff <bundleA_or_runA> <bundleB_or_runB>`

Required behavior:
- Resolves both run inputs.
- Requests diff generation.
- Prints summary and optionally detailed sections.

Key flags:
- `--section` (prompt, retrieval, tool, model, output)
- `--format` (`summary`, `detailed`)
- `--output-file`

Outputs:
- `diff_report_id`
- change summary counts
- attribution hint summary

## Optional Bundle Utility Commands
- `trace bundle export --run <run_id>`
- `trace bundle import --path <bundle_path>`

These commands may be implemented as thin wrappers on bundle API endpoints.

## Exit Codes
- `0`: success.
- `1`: general runtime error.
- `2`: validation or bad input.
- `3`: auth failure.
- `4`: not found.
- `5`: replay completed with simulated steps and strict mode enabled.
- `6`: dependency unavailable or timeout.

## CI Integration Patterns
Pattern A (capture and export on fail):
- Run test command through `trace capture` with `--bundle-on-fail`.
- Upload bundle artifact to CI storage.

Pattern B (post-fail replay):
- Download bundle in debug job.
- Run `trace replay <bundle>`.
- Run `trace diff` against known-good baseline bundle.

## Logging and Diagnostics
- Verbose mode prints request IDs and replay reason codes.
- Error output includes actionable remediation hints.
- JSON output includes stable fields for automated parsing.

## Backward Compatibility
- Flag names remain stable across minor releases.
- Deprecated flags remain for one major release with warnings.

## Cross-References
- API contracts: `docs/06-api-contracts.md`
- Replay semantics: `docs/05-replay-fork-and-diff-engine.md`
- CI workflows and tests: `docs/11-test-plan-and-acceptance.md`
