from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import Event


def find_existing_event_by_idempotency(db: Session, idempotency_key: str) -> Event | None:
    stmt = select(Event).where(Event.idempotency_key == idempotency_key)
    return db.execute(stmt).scalar_one_or_none()
