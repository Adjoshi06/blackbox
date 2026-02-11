from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RunContext:
    run_id: str
    trace_id: str
    step_id: str | None = None
    parent_step_id: str | None = None
    tags: dict[str, Any] = field(default_factory=dict)
    redaction_profile: str = "default"


_current_context: ContextVar[RunContext | None] = ContextVar("trace_run_context", default=None)


def set_current_context(ctx: RunContext | None) -> None:
    _current_context.set(ctx)


def get_current_context() -> RunContext | None:
    return _current_context.get()
