from __future__ import annotations

import time

from backend.app.config import settings
from backend.app.db.session import SessionLocal
from backend.app.modules.replay.service import execute_replay_session
from backend.app.services.jobs import fetch_next_job, mark_job_failure, mark_job_success


def process_one() -> bool:
    with SessionLocal() as db:
        job = fetch_next_job(db)
        if job is None:
            return False

        try:
            if job.job_type == "replay_execute":
                replay_session_id = str(job.payload_json["replay_session_id"])
                execute_replay_session(db, replay_session_id)
            else:
                raise ValueError(f"Unsupported job type: {job.job_type}")
            mark_job_success(db, job)
        except Exception as exc:  # noqa: BLE001
            mark_job_failure(db, job, str(exc))
        return True


def run_forever() -> None:
    interval = max(settings.worker_poll_interval_ms, 100) / 1000.0
    while True:
        handled = process_one()
        if not handled:
            time.sleep(interval)


if __name__ == "__main__":
    run_forever()
