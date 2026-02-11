from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


DeterminismMode = Literal["live", "exact", "cached", "simulated"]
RedactionStatus = Literal["not_required", "redacted", "blocked", "failed"]
ActorType = Literal["sdk", "backend", "replay_engine"]

EVENT_TYPES = {
    "run_started",
    "input_received",
    "prompt_rendered",
    "retrieval_executed",
    "tool_called",
    "tool_result",
    "model_called",
    "model_result",
    "validator_decision",
    "safety_decision",
    "final_output",
    "run_completed",
    "run_failed",
}

REQUIRED_PAYLOAD_FIELDS: dict[str, set[str]] = {
    "run_started": {"app_id", "environment", "entrypoint_name"},
    "input_received": {"input_channels", "input_hash", "input_policy_labels"},
    "prompt_rendered": {
        "prompt_template_id",
        "prompt_template_version",
        "prompt_variables_ref",
        "rendered_prompt_ref",
    },
    "retrieval_executed": {
        "retriever_id",
        "retriever_version",
        "query_text_ref",
        "top_k",
        "filters",
        "candidate_count",
        "candidate_list_ref",
    },
    "tool_called": {"tool_name", "tool_version", "call_signature_hash", "args_ref", "timeout_ms"},
    "tool_result": {"tool_name", "status", "result_ref", "latency_ms"},
    "model_called": {
        "provider",
        "model_id",
        "model_api_version",
        "temperature",
        "top_p",
        "max_tokens",
        "request_ref",
    },
    "model_result": {
        "provider",
        "model_id",
        "finish_reason",
        "token_usage",
        "response_ref",
        "latency_ms",
    },
    "validator_decision": {"validator_name", "validator_version", "decision", "reason_ref"},
    "safety_decision": {"policy_name", "policy_version", "decision", "reason_ref"},
    "final_output": {"output_ref", "response_channel"},
    "run_completed": {"status", "total_steps", "total_latency_ms"},
    "run_failed": {"status", "failed_step_id", "error_class", "error_message_ref"},
}


class ArtifactRef(BaseModel):
    artifact_hash: str
    artifact_type: str
    byte_size: int
    content_encoding: str = "identity"
    mime_type: str = "application/octet-stream"
    redaction_profile: str = "default"


class CanonicalEvent(BaseModel):
    schema_version: str = Field(default="1.0.0")
    trace_id: str
    run_id: str
    step_id: str
    parent_step_id: str | None = None
    sequence_no: int = Field(ge=0)
    event_type: str
    timestamp_utc: datetime
    actor_type: ActorType = "sdk"
    determinism_mode: DeterminismMode = "live"
    artifact_refs: list[ArtifactRef] = Field(default_factory=list)
    redaction_status: RedactionStatus = "not_required"
    payload: dict[str, Any] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    ok: bool
    warnings: list[str] = Field(default_factory=list)


class ReplayPreferences(BaseModel):
    preferred_modes: list[DeterminismMode] = Field(default_factory=lambda: ["exact", "cached", "simulated"])
    fail_on_simulated: bool = False


class PromptOverride(BaseModel):
    template_id: str | None = None
    template_version: str | None = None
    variables: dict[str, Any] = Field(default_factory=dict)


class ModelOverride(BaseModel):
    provider: str | None = None
    model_id: str | None = None


class RetrieverOverride(BaseModel):
    top_k: int | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    embedding_profile: str | None = None


class ReplayOverrideProfile(BaseModel):
    prompt_override: PromptOverride | None = None
    model_override: ModelOverride | None = None
    retriever_override: RetrieverOverride | None = None
    tool_simulation_overrides: dict[str, dict[str, Any]] = Field(default_factory=dict)


class ReplayRequestPayload(BaseModel):
    source_run_id: str
    fork_step_id: str | None = None
    override_profile: ReplayOverrideProfile = Field(default_factory=ReplayOverrideProfile)
    replay_preferences: ReplayPreferences = Field(default_factory=ReplayPreferences)
