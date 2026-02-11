# 10 Operability and SRE

## Purpose
This document defines runtime operations, health, telemetry, and recovery requirements for v1 deployment.

## Deployment Baseline
- Single-node Docker Compose deployment.
- Separate containers for API, worker, UI, Postgres, and MinIO.
- Persistent volumes for database and object store.

## Configuration Model
Configuration categories:
- Service identity and environment.
- Database and object store connection settings.
- Redaction and policy settings.
- Replay and diff worker limits.
- Retention defaults.
- Auth enablement and token configuration.

Configuration requirements:
- Environment variable based.
- Startup-time validation with clear failure messages.
- Runtime config endpoint for non-sensitive effective settings.

## Health and Readiness
Required endpoints:
- Liveness: process up.
- Readiness: dependency connectivity and minimal query checks.

Readiness criteria:
- Postgres reachable.
- MinIO reachable.
- Worker queue connectivity healthy.

## Metrics Specification
System metrics:
- request rate and error rate per endpoint.
- ingest latency percentiles.
- replay session durations and status counts.
- diff generation durations.
- worker queue depth and retry count.

Data metrics:
- events ingested per minute.
- artifact dedup ratio.
- redaction failure rate.
- storage growth by retention class.

Quality metrics aligned to PRD:
- reproducible replay rate.
- mean time to identify root-cause proxy metric.

## Logging Requirements
- Structured JSON logs.
- Required fields: timestamp, service, severity, request_id, run_id, replay_session_id, error_code.
- No sensitive raw payloads in logs.
- Correlation IDs propagated across API and worker processes.

## Alerting Recommendations
Critical alerts:
- sustained ingest error rate above threshold.
- replay failure rate spike.
- redaction failure rate above threshold.
- storage capacity risk in Postgres or MinIO.

Warning alerts:
- high worker queue backlog.
- elevated API latency percentiles.
- repeated dependency timeouts.

## SLO Suggestions for v1
- API availability target: 99.0 percent in single-node baseline.
- Replay job completion success target: 95 percent excluding source data validation failures.
- Ingest p95 latency target defined to maintain less than 5 percent capture overhead.

## Backup and Recovery
- Postgres backups daily with periodic restore tests.
- MinIO snapshots or replication schedule.
- Recovery runbook for restoring metadata and artifacts consistently.

## Incident Runbooks
Runbooks required for:
- ingestion degradation
- replay subsystem failures
- redaction pipeline failures
- storage exhaustion

Runbook minimum sections:
- symptom
- likely causes
- triage steps
- rollback or mitigation actions
- verification checks

## Capacity Planning
- Estimate events per run and average artifact size.
- Project storage by retention class.
- Define thresholds for scale-up triggers.

## Cross-References
- Storage design: `docs/03-data-storage-and-retention.md`
- Security alert topics: `docs/09-security-privacy-compliance.md`
- Acceptance metrics: `docs/11-test-plan-and-acceptance.md`
