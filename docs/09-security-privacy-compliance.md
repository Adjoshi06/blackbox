# 09 Security, Privacy, and Compliance

## Purpose
This document defines security and privacy controls for trace capture, storage, replay, and export workflows.

## Threat Model (v1)
Primary threats:
- PII leakage through raw prompts, tool outputs, and retrieved documents.
- Prompt injection content persisting and spreading through replay.
- Unauthorized access to run traces and CI bundles.
- Tampering with artifacts or replay outputs.

## Data Classification
- Public: non-sensitive system metadata.
- Internal: operational metadata and non-sensitive trace content.
- Sensitive: prompts, user inputs, retrieved text, tool outputs, model outputs.
- Restricted: explicit PII, secrets, credentials, regulated data.

## Redaction Pipeline
Pipeline stages:
1. Field classification from schema tags.
2. Pattern detection (PII and secret patterns).
3. Policy enforcement (denylist, allowlist, hash-only).
4. Output labeling (`redacted`, `blocked`, `failed`).

Policy precedence:
- Denylist beats allowlist.
- Hash-only beats raw storage for sensitive fields.

Failure behavior:
- On redaction failure, artifact is blocked by default.
- Operator override allowed only with explicit policy setting and audit entry.

## Access Control Baseline
- Single-tenant local mode in v1.
- Optional bearer token for API and UI access.
- Role model recommended for extension:
  - `viewer`
  - `debugger`
  - `admin`

Least privilege requirements:
- Replay and export actions require elevated role in multi-user mode.
- Token scopes should separate read, replay, and export permissions.

## Encryption Requirements
- Encryption at rest for Postgres volumes.
- Server-side encryption for MinIO objects.
- TLS for network traffic when deployed beyond localhost.

## Integrity Controls
- Content hash verification on artifact read and replay load.
- Immutable blob object keys by content hash.
- Audit entries for replay creation, override usage, and bundle export/import.

## Bundle Security
- Bundle manifest includes artifact hash list and schema version.
- Sensitive fields remain redacted in exported bundles by default.
- Optional bundle encryption profile for transport and storage.

## Audit Logging
Mandatory auditable actions:
- run and replay creation
- override submission
- diff generation
- bundle export/import
- policy changes

Audit record requirements:
- actor identity
- timestamp UTC
- action type
- target object
- outcome

## Compliance Posture (v1)
- Privacy by default through redaction-first ingestion.
- Data minimization via hash-only storage where possible.
- Retention enforcement with legal hold capability.
- Designed to support SOC2-style controls; formal certification out of v1 scope.

## Incident Response Hooks
- Security event reason codes for blocked redaction and access denial.
- Operational alerting on repeated redaction failures.
- Exportable audit trail for forensic review.

## Cross-References
- Storage and retention controls: `docs/03-data-storage-and-retention.md`
- API auth and error behavior: `docs/06-api-contracts.md`
- Operability and alerting: `docs/10-operability-and-sre.md`
