from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from sdk.python.trace_sdk.client import TraceClient


class ModelCallFn(Protocol):
    def __call__(self, **kwargs: Any) -> Any: ...


@dataclass
class OpenAIChatRequest:
    model: str
    messages: list[dict[str, Any]]
    temperature: float = 0.0
    top_p: float = 1.0
    max_tokens: int = 512
    seed: int | None = None


class OpenAIModelAdapter:
    provider = "openai"

    def __init__(self, trace_client: TraceClient) -> None:
        self.trace = trace_client

    def capture_chat_completion(
        self,
        *,
        run_id: str,
        trace_id: str,
        step_id: str,
        sequence_called: int,
        sequence_result: int,
        request: OpenAIChatRequest,
        call_fn: ModelCallFn,
        model_api_version: str = "v1",
        parent_step_id: str | None = None,
    ) -> Any:
        request_payload = {
            "model": request.model,
            "messages": request.messages,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "max_tokens": request.max_tokens,
            "seed": request.seed,
        }
        signature_hash = self.trace.compute_call_signature_hash(request_payload)

        request_artifact = self.trace.register_artifact(
            artifact_type="model_request",
            content=json.dumps(request_payload, ensure_ascii=True),
            mime_type="application/json",
        )

        self.trace.emit_event(
            run_id=run_id,
            trace_id=trace_id,
            event_type="model_called",
            sequence_no=sequence_called,
            step_id=step_id,
            parent_step_id=parent_step_id,
            payload={
                "provider": self.provider,
                "model_id": request.model,
                "model_api_version": model_api_version,
                "temperature": request.temperature,
                "top_p": request.top_p,
                "max_tokens": request.max_tokens,
                "seed": request.seed,
                "request_ref": request_artifact["artifact_hash"],
                "call_signature_hash": signature_hash,
            },
            artifact_refs=[
                {
                    "artifact_hash": request_artifact["artifact_hash"],
                    "artifact_type": "model_request",
                    "byte_size": len(json.dumps(request_payload, ensure_ascii=True).encode("utf-8")),
                    "mime_type": "application/json",
                    "content_encoding": "identity",
                    "redaction_profile": "default",
                }
            ],
        )

        start = time.perf_counter()
        response = call_fn(**request_payload)
        latency_ms = int((time.perf_counter() - start) * 1000)

        normalized = _normalize_openai_response(response)
        response_artifact = self.trace.register_artifact(
            artifact_type="model_response",
            content=json.dumps(normalized, ensure_ascii=True),
            mime_type="application/json",
        )

        self.trace.emit_event(
            run_id=run_id,
            trace_id=trace_id,
            event_type="model_result",
            sequence_no=sequence_result,
            step_id=step_id,
            parent_step_id=parent_step_id,
            payload={
                "provider": self.provider,
                "model_id": request.model,
                "finish_reason": normalized.get("finish_reason", "unknown"),
                "token_usage": normalized.get(
                    "token_usage",
                    {"prompt": 0, "completion": 0, "total": 0},
                ),
                "response_ref": response_artifact["artifact_hash"],
                "latency_ms": latency_ms,
            },
            artifact_refs=[
                {
                    "artifact_hash": response_artifact["artifact_hash"],
                    "artifact_type": "model_response",
                    "byte_size": len(json.dumps(normalized, ensure_ascii=True).encode("utf-8")),
                    "mime_type": "application/json",
                    "content_encoding": "identity",
                    "redaction_profile": "default",
                }
            ],
        )

        return response


def _normalize_openai_response(response: Any) -> dict[str, Any]:
    if isinstance(response, dict):
        usage = response.get("usage", {})
        choice = (response.get("choices") or [{}])[0]
        return {
            "id": response.get("id", str(uuid.uuid4())),
            "content": choice.get("message", {}).get("content", ""),
            "finish_reason": choice.get("finish_reason", "unknown"),
            "token_usage": {
                "prompt": usage.get("prompt_tokens", 0),
                "completion": usage.get("completion_tokens", 0),
                "total": usage.get("total_tokens", 0),
            },
        }

    usage = getattr(response, "usage", None)
    choices = getattr(response, "choices", [])
    first_choice = choices[0] if choices else None

    prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
    completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
    total_tokens = getattr(usage, "total_tokens", 0) if usage else 0

    content = ""
    finish_reason = "unknown"
    if first_choice is not None:
        message = getattr(first_choice, "message", None)
        content = getattr(message, "content", "") if message else ""
        finish_reason = getattr(first_choice, "finish_reason", "unknown")

    return {
        "id": getattr(response, "id", str(uuid.uuid4())),
        "content": content,
        "finish_reason": finish_reason,
        "token_usage": {
            "prompt": prompt_tokens,
            "completion": completion_tokens,
            "total": total_tokens,
        },
    }


__all__ = ["OpenAIChatRequest", "OpenAIModelAdapter"]
