from __future__ import annotations

import os
from dataclasses import dataclass

import boto3

from backend.app.config import settings


@dataclass
class StoredArtifact:
    bucket: str
    object_key: str


class ArtifactStore:
    def store(self, artifact_hash: str, payload: bytes) -> StoredArtifact:
        raise NotImplementedError

    def exists(self, artifact_hash: str) -> bool:
        raise NotImplementedError


class LocalArtifactStore(ArtifactStore):
    def __init__(self, base_dir: str, bucket: str) -> None:
        self.base_dir = base_dir
        self.bucket = bucket
        os.makedirs(self.base_dir, exist_ok=True)

    def _path_for(self, artifact_hash: str) -> str:
        prefix = artifact_hash[:2]
        folder = os.path.join(self.base_dir, prefix)
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, artifact_hash)

    def store(self, artifact_hash: str, payload: bytes) -> StoredArtifact:
        path = self._path_for(artifact_hash)
        if not os.path.exists(path):
            with open(path, "wb") as handle:
                handle.write(payload)
        return StoredArtifact(bucket=self.bucket, object_key=f"{artifact_hash[:2]}/{artifact_hash}")

    def exists(self, artifact_hash: str) -> bool:
        path = self._path_for(artifact_hash)
        return os.path.exists(path)


class S3ArtifactStore(ArtifactStore):
    def __init__(self) -> None:
        self.bucket = settings.artifact_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint or None,
            aws_access_key_id=settings.s3_access_key or None,
            aws_secret_access_key=settings.s3_secret_key or None,
            region_name=settings.s3_region,
            use_ssl=settings.s3_secure,
        )

    def _key(self, artifact_hash: str) -> str:
        return f"{artifact_hash[:2]}/{artifact_hash}"

    def store(self, artifact_hash: str, payload: bytes) -> StoredArtifact:
        key = self._key(artifact_hash)
        if not self.exists(artifact_hash):
            self.client.put_object(Bucket=self.bucket, Key=key, Body=payload)
        return StoredArtifact(bucket=self.bucket, object_key=key)

    def exists(self, artifact_hash: str) -> bool:
        key = self._key(artifact_hash)
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:  # noqa: BLE001
            return False


def build_artifact_store() -> ArtifactStore:
    if settings.artifact_store_mode.lower() == "s3":
        return S3ArtifactStore()
    return LocalArtifactStore(settings.artifact_local_dir, settings.artifact_bucket)
