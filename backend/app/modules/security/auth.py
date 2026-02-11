from __future__ import annotations

from fastapi import HTTPException, Request, status

from backend.app.config import settings


class AuthContext:
    def __init__(self, actor_id: str, actor_type: str = "user") -> None:
        self.actor_id = actor_id
        self.actor_type = actor_type


def require_auth(request: Request) -> AuthContext:
    if not settings.auth_enabled:
        return AuthContext(actor_id="anonymous", actor_type="local")

    header = request.headers.get("authorization", "")
    prefix = "Bearer "
    if not header.startswith(prefix):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTH_REQUIRED",
                "message": "Authorization token is required",
                "details": {},
                "retryable": False,
            },
        )

    token = header[len(prefix) :]
    if token != settings.auth_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "AUTH_FORBIDDEN",
                "message": "Authorization token is invalid",
                "details": {},
                "retryable": False,
            },
        )

    return AuthContext(actor_id="token_user", actor_type="token")
