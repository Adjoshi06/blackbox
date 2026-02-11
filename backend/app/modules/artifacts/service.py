from __future__ import annotations

import base64
import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.db.models import Artifact
from backend.app.modules.ingestion.validation import EventValidationError
from backend.app.schemas.api import RegisterArtifactRequest
from backend.app.services.artifact_store import ArtifactStore
from backend.app.services.redaction import RedactionEngine


class ArtifactService:
    def __init__(self, store: ArtifactStore, redaction_engine: RedactionEngine) -> None:
        self._store = store
        self._redaction = redaction_engine

    def register_artifact(self, db: Session, req: RegisterArtifactRequest) -> dict[str, object]:
        payload = self._decode_payload(req)

        if payload is None:
            if not req.content_hash:
                raise EventValidationError(
                    "VALIDATION_ERROR",
                    "content_hash is required when artifact payload is omitted",
                    {},
                )

            existing = db.execute(
                select(Artifact).where(Artifact.artifact_hash == req.content_hash)
            ).scalar_one_or_none()
            if existing is not None:
                return {
                    "artifact_hash": existing.artifact_hash,
                    "upload_required": False,
                    "upload_target": {
                        "bucket": existing.storage_bucket,
                        "object_key": existing.storage_object_key,
                    },
                }

            pending = Artifact(
                artifact_hash=req.content_hash,
                artifact_type=req.artifact_type,
                byte_size=req.byte_size,
                mime_type=req.mime_type,
                content_encoding=req.content_encoding,
                redaction_profile=req.redaction_profile,
                storage_bucket=settings.artifact_bucket,
                storage_object_key=f"{req.content_hash[:2]}/{req.content_hash}",
                retention_class=req.retention_class,
                status="pending",
            )
            db.add(pending)
            db.commit()

            return {
                "artifact_hash": req.content_hash,
                "upload_required": True,
                "upload_target": {
                    "bucket": settings.artifact_bucket,
                    "object_key": f"{req.content_hash[:2]}/{req.content_hash}",
                },
            }

        redaction = self._redaction.apply(
            payload,
            field_policies=req.field_policies,
            content_type=req.mime_type,
        )

        if redaction.status == "failed" and settings.redaction_block_on_failure:
            artifact_hash = self._sha256(payload)
            self._upsert_failed_artifact(db, artifact_hash, req, redaction.blocked_reason)
            return {
                "artifact_hash": artifact_hash,
                "upload_required": False,
                "upload_target": {
                    "bucket": settings.artifact_bucket,
                    "object_key": f"{artifact_hash[:2]}/{artifact_hash}",
                },
            }

        artifact_hash = self._sha256(redaction.redacted_bytes)

        existing = db.execute(select(Artifact).where(Artifact.artifact_hash == artifact_hash)).scalar_one_or_none()
        if existing is not None:
            return {
                "artifact_hash": existing.artifact_hash,
                "upload_required": False,
                "upload_target": {
                    "bucket": existing.storage_bucket,
                    "object_key": existing.storage_object_key,
                },
            }

        stored = self._store.store(artifact_hash, redaction.redacted_bytes)
        artifact = Artifact(
            artifact_hash=artifact_hash,
            artifact_type=req.artifact_type,
            byte_size=len(redaction.redacted_bytes),
            mime_type=req.mime_type,
            content_encoding=req.content_encoding,
            redaction_profile=req.redaction_profile,
            storage_bucket=stored.bucket,
            storage_object_key=stored.object_key,
            retention_class=req.retention_class,
            status="blocked" if redaction.status == "blocked" else "ready",
            blocked_reason=redaction.blocked_reason,
        )
        db.add(artifact)
        db.commit()

        return {
            "artifact_hash": artifact_hash,
            "upload_required": False,
            "upload_target": {
                "bucket": stored.bucket,
                "object_key": stored.object_key,
            },
        }

    def _decode_payload(self, req: RegisterArtifactRequest) -> bytes | None:
        if req.content_base64:
            return base64.b64decode(req.content_base64)
        if req.content_text is not None:
            return req.content_text.encode("utf-8")
        return None

    def _upsert_failed_artifact(
        self,
        db: Session,
        artifact_hash: str,
        req: RegisterArtifactRequest,
        blocked_reason: str | None,
    ) -> None:
        existing = db.execute(select(Artifact).where(Artifact.artifact_hash == artifact_hash)).scalar_one_or_none()
        if existing is not None:
            return

        artifact = Artifact(
            artifact_hash=artifact_hash,
            artifact_type=req.artifact_type,
            byte_size=req.byte_size,
            mime_type=req.mime_type,
            content_encoding=req.content_encoding,
            redaction_profile=req.redaction_profile,
            storage_bucket=settings.artifact_bucket,
            storage_object_key=f"{artifact_hash[:2]}/{artifact_hash}",
            retention_class=req.retention_class,
            status="failed",
            blocked_reason=blocked_reason,
        )
        db.add(artifact)
        db.commit()

    @staticmethod
    def _sha256(payload: bytes) -> str:
        return hashlib.sha256(payload).hexdigest()
