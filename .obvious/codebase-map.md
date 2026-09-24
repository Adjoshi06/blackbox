# Codebase map — Blackbox

Depth-2 overview. Leaf counts are files of interest, not totals.

| Path | What it is | Key contents |
|---|---|---|
| `backend/` | FastAPI service — all trace ingestion/query/replay routes | `app/main.py` (routes, envelopes, health), `app/config.py` (env settings), `app/db/models.py`, `app/db/session.py`, `app/db/migrations/` (Alembic, `0001_initial`), `app/schemas/` (API + canonical event models), `app/modules/{ingestion,query,replay,artifacts,security}/`, `app/services/` (artifact store, idempotency, jobs, redaction) |
| `worker/` | Replay job executor (long-running poll loop) | `app/runner.py` — fetches `replay_execute` jobs, executes, marks success/failure |
| `cli/` | Typer CLI distributed as `trace` console script | `trace_cli/main.py` — `capture`, `runs list`, `replay` commands; httpx API client |
| `sdk/python/trace_sdk/` | Python capture SDK | `client.py`, `adapters.py`, `context.py` |
| `web/` | React 18 + Vite 5 cockpit ("Flight Recorder Cockpit") | `src/App.tsx`, `src/api.ts` (typed envelope client), `src/pages/{RunListPage,RunDetailPage,ReplayPage}.tsx`, `vite.config.ts` (host: true, port 5173) |
| `docs/` | Numbered spec documents (00–12) | system overview, architecture, canonical trace spec, storage/retention, capture SDK, replay/diff engine, API contracts, CLI spec, UI spec, security/privacy, operability, test plan, rollout roadmap |
| `ops/` | Deployment topology | `docker-compose.yml` (postgres 16, minio, minio-init, api, worker, web), `env.example` |
| `tests/` | Pytest suite | `unit/`, `integration/test_api_flow.py`, `conftest.py` (SQLite, TestClient, per-test schema reset) |
| Root | Packaging + migration config | `pyproject.toml` (deps, `trace` script, pytest/ruff config), `alembic.ini` (SQLite URL default) |

## Runtime topology (local dev)

```
browser ──> Vite :5173 (web/)  ── calls API ──>  uvicorn :8000 (backend/)
                                 │
trace CLI / trace_sdk ───────────┘
                                 │
                    worker.app.runner (polls jobs table)
                                 │
                    SQLite ./flight_recorder.db + .data/artifacts
              (Postgres + MinIO replace these in ops/docker-compose.yml)
```
