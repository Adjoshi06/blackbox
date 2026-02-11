from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    api_title: str = "LLM Flight Recorder API"
    api_version: str = "0.1.0"
    database_url: str = "sqlite:///./flight_recorder.db"
    auth_enabled: bool = False
    auth_token: str = ""
    artifact_bucket: str = "artifacts"
    artifact_store_mode: str = "local"
    artifact_local_dir: str = ".data/artifacts"
    s3_endpoint: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "us-east-1"
    s3_secure: bool = False
    worker_poll_interval_ms: int = 1000
    redaction_block_on_failure: bool = True

    @staticmethod
    def from_env() -> "Settings":
        def b(name: str, default: bool = False) -> bool:
            value = os.getenv(name)
            if value is None:
                return default
            return value.strip().lower() in {"1", "true", "yes", "on"}

        def i(name: str, default: int) -> int:
            value = os.getenv(name)
            if value is None:
                return default
            try:
                return int(value)
            except ValueError:
                return default

        return Settings(
            api_title=os.getenv("API_TITLE", "LLM Flight Recorder API"),
            api_version=os.getenv("API_VERSION", "0.1.0"),
            database_url=os.getenv("DATABASE_URL", "sqlite:///./flight_recorder.db"),
            auth_enabled=b("AUTH_ENABLED", False),
            auth_token=os.getenv("AUTH_TOKEN", ""),
            artifact_bucket=os.getenv("ARTIFACT_BUCKET", "artifacts"),
            artifact_store_mode=os.getenv("ARTIFACT_STORE_MODE", "local"),
            artifact_local_dir=os.getenv("ARTIFACT_LOCAL_DIR", ".data/artifacts"),
            s3_endpoint=os.getenv("S3_ENDPOINT", ""),
            s3_access_key=os.getenv("S3_ACCESS_KEY", ""),
            s3_secret_key=os.getenv("S3_SECRET_KEY", ""),
            s3_region=os.getenv("S3_REGION", "us-east-1"),
            s3_secure=b("S3_SECURE", False),
            worker_poll_interval_ms=i("WORKER_POLL_INTERVAL_MS", 1000),
            redaction_block_on_failure=b("REDACTION_BLOCK_ON_FAILURE", True),
        )


settings = Settings.from_env()
