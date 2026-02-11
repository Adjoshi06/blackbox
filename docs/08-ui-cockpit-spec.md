# 08 UI Cockpit Specification

## Purpose
This document defines the web cockpit UI behavior for timeline debugging, fork-and-rerun, and run diff analysis.

## Primary Screens
- Run List View.
- Run Detail Cockpit.
- Replay Session View.
- Diff Comparison View.

## Cockpit Layout
Three fixed functional regions in Run Detail:
- Left panel: timeline of steps and key events.
- Center panel: selected step inspector.
- Right panel: fork configuration and replay controls.

## Run List View Requirements
- Filter by app, environment, status, and time range.
- Search by run ID or trace ID.
- Show determinism summary badge for replay runs.
- Show quick actions: open run, export bundle, compare.

## Timeline Panel Requirements
- Ordered by sequence number.
- Event type icons and status indicators.
- Expand/collapse grouped steps.
- Jump-to-error and jump-to-fork markers.

Status colors (must be consistent across UI):
- live/normal
- exact replay
- cached replay
- simulated replay
- failed

## Step Inspector Requirements
For selected step, display:
- metadata summary (event type, timestamps, duration)
- prompt details when relevant
- retrieval candidate table when relevant
- tool arguments/result view when relevant
- model request/result view with token metrics
- safety/validator decisions when present

Data handling:
- Redacted content visibly labeled.
- Hidden sensitive fields show policy reason.

## Fork Configuration Panel Requirements
User can set:
- fork step selection
- prompt template override
- model override
- retriever parameter override
- tool result simulation payload (where permitted)

Validation behavior:
- disallow conflicting overrides.
- preflight validation before replay start.
- clear inline error reasons.

## Replay Session View Requirements
- Live status progression with current step pointer.
- Determinism mode counts (exact, cached, simulated).
- Failure diagnostics with step-level reason codes.
- Action to open derived run on completion.

## Diff Comparison View Requirements
Sections:
- prompt diff
- retrieval diff
- tool diff
- model config diff
- final output diff
- causal attribution summary

Interaction:
- side-by-side and unified text view options.
- filter by changed-only steps.
- jump from diff item back to timeline step.

## Incident Replay Workflow
1. Open failed run from list.
2. Inspect failing or suspect step in timeline.
3. Configure fork overrides in right panel.
4. Start replay and watch status.
5. Open diff against original run.
6. Export findings for team review.

## Usability and Accessibility Requirements
- Keyboard navigation for timeline and diff lists.
- Screen-reader labels for all interactive controls.
- Responsive behavior for desktop and tablet layouts.
- Mobile view supports read-only run inspection for v1.

## Performance Requirements
- Initial run detail render under 2 seconds for medium runs.
- Incremental panel updates without full page refresh.
- Virtualized timeline rendering for large traces.

## Audit and Traceability in UI
- Replay launch records actor identity and override profile ID.
- Export actions log audit events.
- UI displays policy or redaction decisions from backend.

## Cross-References
- API support for views: `docs/06-api-contracts.md`
- Replay and diff semantics: `docs/05-replay-fork-and-diff-engine.md`
- Security controls: `docs/09-security-privacy-compliance.md`
