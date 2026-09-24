---
name: local-dev
description: How to bring Blackbox up locally (API + worker + cockpit), verify it end-to-end, and the pre-existing issues to expect
---

# Local dev — Blackbox (LLM flight recorder)

Recorded by the onboarding run on 2026-09-24 (snapshot `5kj1v527dlxtz6ri93ag:default`).

## Bring-up sequence (verified working)

```bash
pip install -e ".[dev]"                # Python >=3.12; installs trace CLI too
alembic upgrade head                   # SQLite ./flight_recorder.db -> 0001_initial
uvicorn backend.app.main:app --port 8000 &
python -m worker.app.runner &          # replay job executor
cd web && npm install && npm run dev   # cockpit on :5173
```

No env file needed: in-code defaults (SQLite, local artifact store, auth off) match
`ops/env.example`. Postgres + MinIO via `ops/docker-compose.yml` are for the full
topology; this sandbox has no Docker daemon, and everything works on the defaults.

## Verification evidence (from this run)

- `GET /health/live` → `{"status":"ok"}`; `GET /health/ready` → `{"status":"ready"}` (DB round-trip).
- Primary flow: `POST /api/v1/runs` → ingest `run_started` event → `POST .../finalize`
  (`{"final_status":"success"}`) → `POST /api/v1/replays` → worker picked it up →
  replay `completed_exact` with derived run id.
- CLI: `trace capture --run "python3 -c \"print('hello')\""` → live run recorded;
  `trace runs list --output json` returns it.
- Web: Vite dev server 200 on :5173; `npm run build` (tsc + vite) clean.
- `python3 -m pytest`: **4 passed, 1 failed** (pre-existing, see below).
- ruff: 74 pre-existing errors; mypy: 11 pre-existing errors in 4 files.

## Gotchas learned the hard way

1. **Event payload field is `payload`**, not `payload_json` (pydantic model
   `CanonicalEvent`), and `timestamp_utc` is required. `event_type` must be canonical
   and carry its required payload fields — see `REQUIRED_PAYLOAD_FIELDS` in
   `backend/app/schemas/events.py`.
2. **Finalize takes `final_status`** restricted to `"success" | "failed"`; the intuitive
   `"succeeded"` is rejected as a validation error.
3. **Stop the worker before running pytest.** Worker and tests share
   `./flight_recorder.db`; the live worker can consume test-created replay jobs
   concurrently and cause confusing failures. (Note: the one failing test below fails
   even in isolation, so this gotcha is secondary but real.)
4. **Replay requires a terminal source run** — finalize first, then replay.
5. Consecutive event `sequence_no` must be monotonic per run and the first event must
   be `run_started`.
6. Every API response is enveloped: read `body["data"]`, not the body itself.

## Pre-existing issues on master (not caused by setup)

- `tests/integration/test_api_flow.py::test_end_to_end_run_and_replay` fails with
  `sqlite3.IntegrityError: UNIQUE constraint failed: steps.step_id`. The replay engine
  copies source `step_id` into the derived run, but `steps.step_id` is globally unique
  in the schema. Reproduced with services stopped on a fresh DB.
- `ruff check .` → 74 errors (23 auto-fixable). `mypy backend worker sdk cli` → 11
  errors in 4 files.
- `POST /api/v1/diffs*` and `POST /api/v1/bundles/*` are 501 stubs (M3 roadmap scope).
