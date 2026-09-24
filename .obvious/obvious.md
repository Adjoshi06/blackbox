# Blackbox (Adjoshi06/blackbox)

"Flight recorder" for LLM systems: deterministic, replayable traces of every decision
and artifact, plus a time-travel cockpit UI for fork-and-re-run debugging.

## Stack

- **Backend API** — Python >=3.12, FastAPI, SQLAlchemy 2, Alembic (`backend/`), port **8000**
- **Worker** — Python process that executes replay jobs (`worker/`)
- **CLI** — Typer app, entry point `trace` (`cli/`)
- **SDK** — Python package `trace_sdk` (`sdk/python/trace_sdk/`)
- **Web cockpit** — React 18 + Vite 5 + TypeScript (`web/`), port **5173**
- **Storage** — SQLite + local artifact dir by default; Postgres 16 + MinIO via `ops/docker-compose.yml` for the full deployment topology (Docker is not available in this sandbox, so local dev runs on the repo's SQLite/local-store defaults, which are also what the test suite uses)

## Commands (from repo root unless noted)

```bash
# Install (dev extras include pytest, ruff, mypy)
pip install -e ".[dev]"

# Database migrations (SQLite by default)
alembic upgrade head
alembic current                       # expect 0001_initial (head)

# API server (canonical dev command, port 8000)
uvicorn backend.app.main:app --reload --port 8000

# Worker (replay job executor)
python -m worker.app.runner

# Web cockpit (Vite dev server, port 5173)
cd web && npm install && npm run dev
cd web && npm run build               # typecheck + production build

# CLI (talks to API on http://localhost:8000)
trace capture --run "python3 -c \"print('hello')\""
trace runs list --output json

# Full dockerized topology (Postgres + MinIO + API + worker + web)
cd ops && docker compose up --build
```

## Environment variables

Defaults live in `ops/env.example` and `backend/app/config.py`. For local dev, the
in-code defaults already work (SQLite, local artifact store, auth disabled) — no env
file or secrets are required. Keys: `DATABASE_URL`, `AUTH_ENABLED`, `AUTH_TOKEN`,
`ARTIFACT_STORE_MODE`, `ARTIFACT_LOCAL_DIR`, `S3_ENDPOINT`, `S3_ACCESS_KEY`,
`S3_SECRET_KEY`, `S3_REGION`, `S3_SECURE`, `WORKER_POLL_INTERVAL_MS`,
`REDACTION_BLOCK_ON_FAILURE`.

## Codebase map

See [codebase-map.md](codebase-map.md) for the folder-level table. Quick orientation:
`backend/app/main.py` (all routes), `backend/app/config.py` (settings), `backend/app/db/`
(models + Alembic migrations), `backend/app/modules/` (ingestion, query, replay,
artifacts, security), `worker/app/runner.py` (job loop), `cli/trace_cli/main.py`
(`trace`), `web/src/` (cockpit pages), `docs/` (13 numbered spec documents),
`ops/` (compose + env example), `tests/unit` + `tests/integration`.

## Local verification (what "working" looks like)

1. `curl localhost:8000/health/live` → `{"status":"ok"}`;
   `curl localhost:8000/health/ready` → `{"status":"ready"}` (DB round-trip).
2. Primary flow — capture → query → replay:
   `trace capture --run "python3 -c \"print('hello')\""` prints a run_id;
   `trace runs list --output json` shows the run;
   `POST /api/v1/replays` on a finalized run goes `pending` → `completed_exact`
   once the worker picks it up.
3. Web cockpit serves on http://localhost:5173 (HTTP 200, title "Flight Recorder Cockpit").
4. `python3 -m pytest` from repo root.
5. Web `npm run build` in `web/` passes.

## API notes (verified live)

- Event ingest: the event object field is **`payload`** (not `payload_json`); event
  `timestamp_utc` is required; `event_type` must be one of the canonical types with
  their required payload fields (see `backend/app/schemas/events.py`).
- Finalize: body is `{"final_status": "success" | "failed"}` (not "succeeded").
- Replay requires a terminal (finalized) source run.
- Envelope: every response is `{request_id, status, data, error}`; errors use
  `VALIDATION_ERROR` / `CONFLICT` / `NOT_FOUND` codes.

## Snapshot

- `snapshotId: 5kj1v527dlxtz6ri93ag:default`
- Captured: 2026-09-24T19:22:44.490Z (dev stack running: API :8000, worker, Vite :5173)

## Local verification summary

- **dev_stack_healthy: true** — API, worker, and web all running and verified.
- Primary flow evidence: API create-run → ingest `run_started` → finalize → replay
  `completed_exact` (worker processed it); CLI `trace capture` live run captured and
  listed via `trace runs list`; web dev server HTTP 200 + clean production build.
- pytest: 4 passed / 1 failed — the failure is a **pre-existing master bug**
  (`tests/integration/test_api_flow.py::test_end_to_end_run_and_replay` raises
  `sqlite3.IntegrityError: UNIQUE constraint failed: steps.step_id`; replay-derived
  runs reuse source `step_id` which the schema keeps globally unique). Reproduced in
  isolation on a fresh DB, so it is not caused by this onboarding run.
- ruff: 74 pre-existing errors; mypy: 11 pre-existing errors in 4 files — pre-existing
  debt on master, untouched here.
- Gotcha: the worker and pytest both use `./flight_recorder.db`; stop the worker
  before running pytest or tests can fail on concurrent writes.

## Known limitations

- `POST /api/v1/diffs*` and `POST /api/v1/bundles/*` return 501 (M3 scope, not implemented).
- Docker/Compose topology could not be exercised in this sandbox (no Docker daemon);
  instructions above are from the repo's own compose file and Dockerfiles.
