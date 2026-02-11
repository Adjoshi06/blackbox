from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import typer


app = typer.Typer(help="Trace CLI for LLM Flight Recorder")
runs_app = typer.Typer(help="Run query commands")
app.add_typer(runs_app, name="runs")


EXIT_SUCCESS = 0
EXIT_RUNTIME_ERROR = 1
EXIT_VALIDATION = 2
EXIT_AUTH = 3
EXIT_NOT_FOUND = 4
EXIT_SIMULATED_STRICT = 5
EXIT_DEP_UNAVAILABLE = 6


class ApiClient:
    def __init__(self, api_url: str, auth_token: str | None, timeout: float, verbose: bool = False) -> None:
        self.api_url = api_url.rstrip("/")
        self.auth_token = auth_token
        self.timeout = timeout
        self.verbose = verbose
        self.client = httpx.Client(timeout=timeout)

    def close(self) -> None:
        self.client.close()

    def call(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        headers: dict[str, str] = {"content-type": "application/json"}
        if self.auth_token:
            headers["authorization"] = f"Bearer {self.auth_token}"
        url = f"{self.api_url}{path}"
        try:
            response = self.client.request(method, url, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise RuntimeError(f"Dependency unavailable: {exc}") from exc
        except httpx.TransportError as exc:
            raise RuntimeError(f"Dependency unavailable: {exc}") from exc

        body = response.json()
        if self.verbose:
            request_id = body.get("request_id")
            if request_id:
                typer.echo(f"request_id={request_id}", err=True)

        if response.status_code >= 400:
            error = body.get("error") or {}
            message = error.get("message", "request failed")
            code = error.get("code", "INTERNAL_ERROR")
            raise ApiError(code=code, message=message, status_code=response.status_code)

        return body["data"]


class ApiError(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def _print(payload: Any, output: str) -> None:
    if output == "json":
        typer.echo(json.dumps(payload, indent=2, default=str))
    else:
        if isinstance(payload, dict):
            for key, value in payload.items():
                typer.echo(f"{key}: {value}")
        elif isinstance(payload, list):
            for item in payload:
                typer.echo(str(item))
        else:
            typer.echo(str(payload))


def _map_error_to_exit(err: Exception) -> int:
    if isinstance(err, ApiError):
        if err.code in {"VALIDATION_ERROR", "CONFLICT"}:
            return EXIT_VALIDATION
        if err.code in {"AUTH_REQUIRED", "AUTH_FORBIDDEN"}:
            return EXIT_AUTH
        if err.code == "NOT_FOUND":
            return EXIT_NOT_FOUND
        if err.code == "DEPENDENCY_UNAVAILABLE":
            return EXIT_DEP_UNAVAILABLE
        return EXIT_RUNTIME_ERROR
    if "Dependency unavailable" in str(err):
        return EXIT_DEP_UNAVAILABLE
    return EXIT_RUNTIME_ERROR


@app.command("capture")
def capture(
    run_command: str = typer.Option(..., "--run"),
    app_id: str = typer.Option("local-app", "--app-id"),
    env: str = typer.Option("local", "--env"),
    retention_class: str = typer.Option("dev_short", "--retention-class"),
    bundle_on_fail: bool = typer.Option(False, "--bundle-on-fail"),
    api_url: str = typer.Option("http://localhost:8000", "--api-url"),
    auth_token: str | None = typer.Option(None, "--auth-token"),
    output: str = typer.Option("text", "--output"),
    timeout: float = typer.Option(10.0, "--timeout"),
    verbose: bool = typer.Option(False, "--verbose"),
) -> None:
    client = ApiClient(api_url, auth_token, timeout, verbose=verbose)
    try:
        run = client.call(
            "POST",
            "/api/v1/runs",
            {
                "app_id": app_id,
                "environment": env,
                "source_type": "live",
                "retention_class": retention_class,
                "tags": {"capture_cli": True},
            },
        )

        run_id = run["run_id"]
        trace_id = run["trace_id"]
        lifecycle_step_id = str(uuid.uuid4())

        client.call(
            "POST",
            f"/api/v1/runs/{run_id}/events",
            {
                "idempotency_key": f"{run_id}:{lifecycle_step_id}:run_started:0",
                "event": {
                    "schema_version": "1.0.0",
                    "trace_id": trace_id,
                    "run_id": run_id,
                    "step_id": lifecycle_step_id,
                    "parent_step_id": None,
                    "sequence_no": 0,
                    "event_type": "run_started",
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "actor_type": "sdk",
                    "determinism_mode": "live",
                    "artifact_refs": [],
                    "redaction_status": "not_required",
                    "payload": {
                        "app_id": app_id,
                        "environment": env,
                        "entrypoint_name": run_command,
                        "user_session_ref": None,
                        "input_summary_ref": None,
                    },
                },
            },
        )

        child_env = os.environ.copy()
        child_env["TRACE_API_URL"] = api_url
        child_env["TRACE_AUTH_TOKEN"] = auth_token or ""
        child_env["TRACE_RUN_ID"] = run_id
        child_env["TRACE_TRACE_ID"] = trace_id

        proc = subprocess.run(run_command, shell=True, env=child_env, check=False)
        terminal_event_type = "run_completed" if proc.returncode == 0 else "run_failed"
        terminal_payload = (
            {"status": "success", "total_steps": 2, "total_latency_ms": 0}
            if proc.returncode == 0
            else {
                "status": "failed",
                "failed_step_id": lifecycle_step_id,
                "error_class": "SubprocessError",
                "error_message_ref": f"command_exit_code_{proc.returncode}",
            }
        )

        client.call(
            "POST",
            f"/api/v1/runs/{run_id}/events",
            {
                "idempotency_key": f"{run_id}:{lifecycle_step_id}:{terminal_event_type}:1",
                "event": {
                    "schema_version": "1.0.0",
                    "trace_id": trace_id,
                    "run_id": run_id,
                    "step_id": lifecycle_step_id,
                    "parent_step_id": None,
                    "sequence_no": 1,
                    "event_type": terminal_event_type,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "actor_type": "sdk",
                    "determinism_mode": "live",
                    "artifact_refs": [],
                    "redaction_status": "not_required",
                    "payload": terminal_payload,
                },
            },
        )

        client.call(
            "POST",
            f"/api/v1/runs/{run_id}/finalize",
            {"final_status": "success" if proc.returncode == 0 else "failed"},
        )

        output_payload = {
            "run_id": run_id,
            "trace_id": trace_id,
            "command_exit_code": proc.returncode,
            "bundle_exported": False,
        }
        _print(output_payload, output)

        if proc.returncode != 0 and bundle_on_fail:
            typer.echo(
                "bundle-on-fail is reserved for M3 bundle workflows and is not yet implemented",
                err=True,
            )

        raise typer.Exit(code=proc.returncode)
    except Exception as err:  # noqa: BLE001
        typer.echo(f"error: {err}", err=True)
        raise typer.Exit(code=_map_error_to_exit(err)) from err
    finally:
        client.close()


@app.command("replay")
def replay(
    bundle_or_run_ref: str,
    fork_step: str | None = typer.Option(None, "--fork-step"),
    override_profile: Path | None = typer.Option(None, "--override-profile"),
    wait: bool = typer.Option(False, "--wait"),
    fail_on_simulated: bool = typer.Option(False, "--fail-on-simulated"),
    api_url: str = typer.Option("http://localhost:8000", "--api-url"),
    auth_token: str | None = typer.Option(None, "--auth-token"),
    output: str = typer.Option("text", "--output"),
    timeout: float = typer.Option(10.0, "--timeout"),
    verbose: bool = typer.Option(False, "--verbose"),
) -> None:
    client = ApiClient(api_url, auth_token, timeout, verbose=verbose)
    try:
        profile = {}
        if override_profile:
            profile = json.loads(override_profile.read_text(encoding="utf-8"))

        created = client.call(
            "POST",
            "/api/v1/replays",
            {
                "source_run_id": bundle_or_run_ref,
                "fork_step_id": fork_step,
                "override_profile": profile,
                "replay_preferences": {
                    "preferred_modes": ["exact", "cached", "simulated"],
                    "fail_on_simulated": fail_on_simulated,
                },
            },
        )
        replay_session_id = created["replay_session_id"]

        if not wait:
            _print(created, output)
            raise typer.Exit(code=EXIT_SUCCESS)

        terminal = None
        while True:
            status = client.call("GET", f"/api/v1/replays/{replay_session_id}")
            if verbose:
                typer.echo(f"status={status['status']}", err=True)

            if status["status"] not in {"pending", "running"}:
                terminal = status
                break
            time.sleep(1)

        _print(terminal, output)

        if fail_on_simulated and terminal and terminal["status"] in {"completed_simulated", "completed_mixed"}:
            raise typer.Exit(code=EXIT_SIMULATED_STRICT)

        raise typer.Exit(code=EXIT_SUCCESS)
    except typer.Exit:
        raise
    except Exception as err:  # noqa: BLE001
        typer.echo(f"error: {err}", err=True)
        raise typer.Exit(code=_map_error_to_exit(err)) from err
    finally:
        client.close()


@runs_app.command("list")
def runs_list(
    app_id: str | None = typer.Option(None, "--app-id"),
    environment: str | None = typer.Option(None, "--env"),
    status: str | None = typer.Option(None, "--status"),
    api_url: str = typer.Option("http://localhost:8000", "--api-url"),
    auth_token: str | None = typer.Option(None, "--auth-token"),
    output: str = typer.Option("text", "--output"),
    timeout: float = typer.Option(10.0, "--timeout"),
    verbose: bool = typer.Option(False, "--verbose"),
) -> None:
    client = ApiClient(api_url, auth_token, timeout, verbose=verbose)
    try:
        params = []
        if app_id:
            params.append(f"app_id={app_id}")
        if environment:
            params.append(f"environment={environment}")
        if status:
            params.append(f"status={status}")
        query = f"?{'&'.join(params)}" if params else ""
        data = client.call("GET", f"/api/v1/runs{query}")
        _print(data, output)
    except Exception as err:  # noqa: BLE001
        typer.echo(f"error: {err}", err=True)
        raise typer.Exit(code=_map_error_to_exit(err)) from err
    finally:
        client.close()


@runs_app.command("get")
def runs_get(
    run_id: str,
    api_url: str = typer.Option("http://localhost:8000", "--api-url"),
    auth_token: str | None = typer.Option(None, "--auth-token"),
    output: str = typer.Option("text", "--output"),
    timeout: float = typer.Option(10.0, "--timeout"),
    verbose: bool = typer.Option(False, "--verbose"),
) -> None:
    client = ApiClient(api_url, auth_token, timeout, verbose=verbose)
    try:
        data = client.call("GET", f"/api/v1/runs/{run_id}")
        _print(data, output)
    except Exception as err:  # noqa: BLE001
        typer.echo(f"error: {err}", err=True)
        raise typer.Exit(code=_map_error_to_exit(err)) from err
    finally:
        client.close()


def run() -> None:
    app()


if __name__ == "__main__":
    run()
