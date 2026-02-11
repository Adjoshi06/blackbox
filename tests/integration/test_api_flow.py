from __future__ import annotations

from datetime import datetime, timezone

from worker.app.runner import process_one


def _event(
    *,
    trace_id: str,
    run_id: str,
    step_id: str,
    sequence_no: int,
    event_type: str,
    payload: dict,
) -> dict:
    return {
        "schema_version": "1.0.0",
        "trace_id": trace_id,
        "run_id": run_id,
        "step_id": step_id,
        "parent_step_id": None,
        "sequence_no": sequence_no,
        "event_type": event_type,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "actor_type": "sdk",
        "determinism_mode": "live",
        "artifact_refs": [],
        "redaction_status": "not_required",
        "payload": payload,
    }


def _post_event(client, run_id: str, idem: str, event: dict):
    return client.post(
        f"/api/v1/runs/{run_id}/events",
        json={
            "idempotency_key": idem,
            "event": event,
        },
    )


def test_end_to_end_run_and_replay(client) -> None:
    create_response = client.post(
        "/api/v1/runs",
        json={
            "app_id": "test-app",
            "environment": "test",
            "source_type": "live",
            "tags": {},
        },
    )
    assert create_response.status_code == 200
    create_data = create_response.json()["data"]
    run_id = create_data["run_id"]
    trace_id = create_data["trace_id"]

    step_id = "step-source"

    started = _event(
        trace_id=trace_id,
        run_id=run_id,
        step_id=step_id,
        sequence_no=0,
        event_type="run_started",
        payload={
            "app_id": "test-app",
            "environment": "test",
            "entrypoint_name": "pytest",
            "user_session_ref": None,
            "input_summary_ref": None,
        },
    )
    response = _post_event(client, run_id, "idem-0", started)
    assert response.status_code == 200

    completed = _event(
        trace_id=trace_id,
        run_id=run_id,
        step_id=step_id,
        sequence_no=1,
        event_type="run_completed",
        payload={
            "status": "success",
            "total_steps": 1,
            "total_latency_ms": 10,
        },
    )
    response = _post_event(client, run_id, "idem-1", completed)
    assert response.status_code == 200

    replay_response = client.post(
        "/api/v1/replays",
        json={
            "source_run_id": run_id,
            "fork_step_id": step_id,
            "override_profile": {
                "model_override": {
                    "provider": "openai",
                    "model_id": "gpt-4.1-mini",
                }
            },
            "replay_preferences": {
                "preferred_modes": ["exact", "cached", "simulated"],
                "fail_on_simulated": False,
            },
        },
    )
    assert replay_response.status_code == 200
    replay_session_id = replay_response.json()["data"]["replay_session_id"]

    assert process_one() is True

    status_response = client.get(f"/api/v1/replays/{replay_session_id}")
    assert status_response.status_code == 200
    status_payload = status_response.json()["data"]
    assert status_payload["status"] in {"completed_exact", "completed_mixed", "completed_simulated"}
    assert status_payload["derived_run_id"] is not None


def test_event_idempotency_returns_prior_response(client) -> None:
    create_response = client.post(
        "/api/v1/runs",
        json={
            "app_id": "test-app",
            "environment": "test",
            "source_type": "live",
            "tags": {},
        },
    )
    run_id = create_response.json()["data"]["run_id"]
    trace_id = create_response.json()["data"]["trace_id"]

    step_id = "step-one"
    event = _event(
        trace_id=trace_id,
        run_id=run_id,
        step_id=step_id,
        sequence_no=0,
        event_type="run_started",
        payload={
            "app_id": "test-app",
            "environment": "test",
            "entrypoint_name": "pytest",
            "user_session_ref": None,
            "input_summary_ref": None,
        },
    )

    first = _post_event(client, run_id, "same-idem", event)
    second = _post_event(client, run_id, "same-idem", event)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"]["event_id"] == second.json()["data"]["event_id"]
    assert second.json()["data"]["accepted"] is False
