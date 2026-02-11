from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from backend.app.db.models import Job


def _now() -> datetime:
    return datetime.now(timezone.utc)


def fetch_next_job(db: Session, job_type: str | None = None) -> Job | None:
    stmt = select(Job).where(
        and_(
            Job.status == "pending",
            Job.available_at_utc <= _now(),
        )
    )
    if job_type:
        stmt = stmt.where(Job.job_type == job_type)
    stmt = stmt.order_by(Job.created_at_utc.asc()).limit(1)
    job = db.execute(stmt).scalar_one_or_none()
    if job is None:
        return None
    job.status = "running"
    job.updated_at_utc = _now()
    db.commit()
    db.refresh(job)
    return job


def mark_job_success(db: Session, job: Job) -> None:
    job.status = "completed"
    job.updated_at_utc = _now()
    db.commit()


def mark_job_failure(db: Session, job: Job, error: str) -> None:
    job.retries += 1
    job.last_error = error
    job.updated_at_utc = _now()
    if job.retries >= job.max_retries:
        job.status = "failed"
    else:
        backoff = 2 ** min(job.retries, 6)
        job.status = "pending"
        job.available_at_utc = _now() + timedelta(seconds=backoff)
    db.commit()
