from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

# Keep tests on local sqlite by default.
os.environ.setdefault("DATABASE_URL", "sqlite:///./flight_recorder.db")
os.environ.setdefault("AUTH_ENABLED", "false")

from backend.app.db.session import Base, engine  # noqa: E402
from backend.app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
