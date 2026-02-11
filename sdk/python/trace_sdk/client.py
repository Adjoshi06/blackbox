from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from sdk.python.trace_sdk.context import RunContext, get_current_context, set_current_context


class TraceClient:
    def __init__(
        self,
        api_url: str = "http://localhost:8000",
        auth_token: str | None = None,
        timeout: float = 10.0,
        max_retries: int = 3,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.auth_token = auth_token
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = httpx.Client(timeout=timeout)

    @classmethod
    def from_env(cls) -> "TraceClient":
        return cls(
            api_url=os.getenv("TRACE_API_URL", "http://localhost:8000"),
            auth_token=os.getenv("TRACE_AUTH_TOKEN"),
            timeout=float(os.getenv("TRACE_TIMEOUT", "10")),
            max_retries=int(os.getenv("TRACE_MAX_RETRIES", "3")),
        )

    def start_run(
        self,
        app_id: str,
        environment: str,
        source_type: str = "live",
        tags: dict[str, Any] | None = None,
    ) -> RunContext:
        response = self._request(
            "POST",
            "/api/v1/runs",
            json={
                "app_id": app_id,
                "environment": environment,
                "source_type": source_type,
                "tags": tags or {},
            },
        )
        payload = response["data"]
        ctx = RunContext(run_id=payload["run_id"], trace_id=payload["trace_id"], tags=tags or {})
        set_current_context(ctx)
        return ctx

    def finalize_run(self, run_id: str, final_status: str) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/api/v1/runs/{run_id}/finalize",
            json={"final_status": final_status},
        )["data"]

    def emit_event(
        self,
        *,
        event_type: str,
        sequence_no: int,
        step_id: str,
        payload: dict[str, Any],
        parent_step_id: str | None = None,
        determinism_mode: str = "live",
        actor_type: str = "sdk",
        artifact_refs: list[dict[str, Any]] | None = None,
        redaction_status: str = "not_required",
        schema_version: str = "1.0.0",
        idempotency_key: str | None = None,
        run_id: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        ctx = get_current_context()
        resolved_run_id = run_id or (ctx.run_id if ctx else None)
        resolved_trace_id = trace_id or (ctx.trace_id if ctx else None)
        if not resolved_run_id or not resolved_trace_id:
            raise ValueError("run_id and trace_id are required either directly or via context")

        idem = idempotency_key or self._idem_key(resolved_run_id, step_id, event_type, sequence_no)
        event = {
            "schema_version": schema_version,
            "trace_id": resolved_trace_id,
            "run_id": resolved_run_id,
            "step_id": step_id,
            "parent_step_id": parent_step_id,
            "sequence_no": sequence_no,
            "event_type": event_type,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "actor_type": actor_type,
            "determinism_mode": determinism_mode,
            "artifact_refs": artifact_refs or [],
            "redaction_status": redaction_status,
            "payload": payload,
        }
        return self._request(
            "POST",
            f"/api/v1/runs/{resolved_run_id}/events",
            json={"idempotency_key": idem, "event": event},
        )["data"]

    def register_artifact(
        self,
        *,
        artifact_type: str,
        content: str | bytes,
        mime_type: str = "text/plain",
        redaction_profile: str = "default",
        retention_class: str = "dev_short",
        field_policies: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if isinstance(content, str):
            payload_bytes = content.encode("utf-8")
        else:
            payload_bytes = content

        content_base64 = base64.b64encode(payload_bytes).decode("ascii")
        body = {
            "artifact_type": artifact_type,
            "byte_size": len(payload_bytes),
            "mime_type": mime_type,
            "redaction_profile": redaction_profile,
            "retention_class": retention_class,
            "content_base64": content_base64,
            "field_policies": field_policies or {},
        }
        return self._request("POST", "/api/v1/artifacts", json=body)["data"]

    def compute_call_signature_hash(self, payload: dict[str, Any]) -> str:
        normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def close(self) -> None:
        self._client.close()

    def _request(self, method: str, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.api_url}{path}"
        headers = {"content-type": "application/json"}
        if self.auth_token:
            headers["authorization"] = f"Bearer {self.auth_token}"

        attempts = 0
        while True:
            attempts += 1
            response = self._client.request(method, url, json=json, headers=headers)
            if response.status_code < 500:
                break
            if attempts > self.max_retries:
                break
            time.sleep(0.2 * attempts)

        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "success":
            message = payload.get("error", {}).get("message", "unknown error")
            raise RuntimeError(message)
        return payload

    @staticmethod
    def _idem_key(run_id: str, step_id: str, event_type: str, sequence_no: int) -> str:
        return f"{run_id}:{step_id}:{event_type}:{sequence_no}"


__all__ = ["TraceClient", "RunContext", "set_current_context", "get_current_context"]
