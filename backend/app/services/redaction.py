from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any


EMAIL_PATTERN = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
PHONE_PATTERN = re.compile(r"\b(?:\+1[-. ]?)?\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}\b")
SECRET_PATTERN = re.compile(r"(?i)\b(api[_-]?key|secret|token|password)\s*[:=]\s*[^\s,;]+")


@dataclass
class RedactionResult:
    redacted_bytes: bytes
    status: str
    decisions: dict[str, str]
    blocked_reason: str | None


class RedactionEngine:
    def __init__(
        self,
        denylist_fields: set[str] | None = None,
        allowlist_fields: set[str] | None = None,
    ) -> None:
        self._denylist = denylist_fields or set()
        self._allowlist = allowlist_fields or set()

    def redact_text(self, text: str) -> tuple[str, bool]:
        updated = text
        changed = False
        for pattern, replacement in (
            (EMAIL_PATTERN, "[REDACTED_EMAIL]"),
            (SSN_PATTERN, "[REDACTED_SSN]"),
            (PHONE_PATTERN, "[REDACTED_PHONE]"),
            (SECRET_PATTERN, "[REDACTED_SECRET]"),
        ):
            updated_2, count = pattern.subn(replacement, updated)
            if count > 0:
                changed = True
                updated = updated_2
        return updated, changed

    def apply(
        self,
        payload: bytes,
        field_policies: dict[str, str] | None = None,
        content_type: str = "text/plain",
    ) -> RedactionResult:
        policies = field_policies or {}
        decisions: dict[str, str] = {}
        try:
            decoded = payload.decode("utf-8", errors="replace")
            blocked_reason = None

            if content_type == "application/json":
                obj = json.loads(decoded)
                redacted = self._apply_json(obj, policies, decisions)
                encoded = json.dumps(redacted, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
                status = "redacted" if decisions else "not_required"
                if "blocked" in decisions.values():
                    status = "blocked"
                    blocked_reason = "policy_blocked_field"
                return RedactionResult(encoded, status, decisions, blocked_reason)

            redacted_text, changed = self.redact_text(decoded)
            status = "redacted" if changed else "not_required"
            return RedactionResult(redacted_text.encode("utf-8"), status, decisions, None)
        except Exception as exc:  # noqa: BLE001
            return RedactionResult(payload, "failed", decisions, str(exc))

    def _apply_json(self, obj: Any, policies: dict[str, str], decisions: dict[str, str]) -> Any:
        if isinstance(obj, dict):
            output: dict[str, Any] = {}
            for key, value in obj.items():
                policy = policies.get(key)
                if key in self._denylist:
                    policy = "drop"
                elif key in self._allowlist and policy is None:
                    policy = "raw_allowed"

                if policy == "drop":
                    decisions[key] = "blocked"
                    continue

                if policy == "hash_only":
                    decisions[key] = "hash_only"
                    output[key] = self._digest_text(json.dumps(value, sort_keys=True, ensure_ascii=True))
                    continue

                if isinstance(value, str):
                    redacted, changed = self.redact_text(value)
                    output[key] = redacted
                    if changed:
                        decisions[key] = "redacted"
                else:
                    output[key] = self._apply_json(value, policies, decisions)
            return output

        if isinstance(obj, list):
            return [self._apply_json(item, policies, decisions) for item in obj]

        return obj

    @staticmethod
    def _digest_text(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
