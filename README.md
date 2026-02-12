#  Blackbox

Blackbox is a “flight recorder” for LLM systems (RAG, agents, tool use) that captures every decision and artifact in a deterministic, replayable trace. It includes a **time-travel cockpit UI** that lets you rewind to any step, swap a component (prompt/retriever/model), and re-run from that point to see causal impacts.

## Stack
- FastAPI backend (`backend/`)
- Worker process (`worker/`)
- Postgres + MinIO (Docker Compose)
- React cockpit UI (`web/`)
- Python SDK (`sdk/python/trace_sdk`)
- Python CLI (`trace`)

## Quick start (local)

1. Install Python deps:
```bash
pip install -e .[dev]
```

2. Start API:
```bash
uvicorn backend.app.main:app --reload --port 8000
```

3. Start worker:
```bash
python -m worker.app.runner
```

4. Start web UI:
```bash
cd web
npm install
npm run dev
```

## Docker compose

```bash
cd ops
docker compose up --build
```

## CLI examples

```bash
trace capture --run "python -c \"print('hello')\""
trace runs list --output json
trace replay <run_id> --wait
```

## API base
`/api/v1`

Implemented endpoints:
- `POST /runs`
- `POST /runs/{run_id}/events`
- `POST /artifacts`
- `POST /runs/{run_id}/finalize`
- `GET /runs`
- `GET /runs/{run_id}`
- `GET /runs/{run_id}/events`
- `GET /artifacts/{artifact_hash}`
- `POST /replays`
- `GET /replays/{replay_session_id}`
- `POST /replays/{replay_session_id}/cancel`
