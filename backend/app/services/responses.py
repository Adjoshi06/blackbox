from __future__ import annotations

import uuid
from typing import Any

from fastapi import Request


def request_id(request: Request) -> str:
    existing = request.headers.get("x-request-id")
    return existing if existing else str(uuid.uuid4())


def success_envelope(req_id: str, data: Any) -> dict[str, Any]:
    return {
        "request_id": req_id,
        "status": "success",
        "data": data,
        "error": None,
    }


def error_envelope(
    req_id: str,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    retryable: bool = False,
) -> dict[str, Any]:
    return {
        "request_id": req_id,
        "status": "error",
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "retryable": retryable,
        },
    }
