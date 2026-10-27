"""Background worker process executing durable asynchronous jobs."""
import logging
import os
import time
from uuid import uuid4

from sqlalchemy.orm import Session

from app.contracts.enums import JobKind
from app.db.session import SessionLocal, get_db
from app.main import app
from app.services.imports import run_import_job
from app.services.jobs import acquire_next_job, get_job_by_id

logger = logging.getLogger(__name__)


def _get_worker_session(db: Session | None = None) -> tuple[Session, bool]:
    if db is not None:
        return db, False
    if get_db in app.dependency_overrides:
        gen = app.dependency_overrides[get_db]()
        return next(gen), False
    return SessionLocal(), True


def process_single_job(job_id: str, db: Session | None = None) -> None:
    """Execute a specific job synchronously within a worker session."""
    session, should_close = _get_worker_session(db)
    try:
        job = get_job_by_id(session, job_id)
        if job.kind == JobKind.IMPORT_RECORDS.value:
            run_import_job(session, job)
        else:
            logger.warning("Unrecognized job kind '%s' for job %s", job.kind, job_id)
    finally:
        if should_close:
            session.close()


def poll_and_execute_next(worker_id: str | None = None, db: Session | None = None) -> bool:
    """Check for queued work, claim it under worker lease, and execute."""
    w_id = worker_id or f"worker-{os.getpid()}-{uuid4().hex[:8]}"
    session, should_close = _get_worker_session(db)
    try:
        job = acquire_next_job(session, worker_id=w_id, lease_seconds=120)
        if not job:
            return False

        logger.info("Worker %s claimed job %s (kind=%s)", w_id, job.id, job.kind)
        if job.kind == JobKind.IMPORT_RECORDS.value:
            run_import_job(session, job)
        return True
    finally:
        if should_close:
            session.close()


def run_worker_daemon(poll_interval: float = 1.0, max_iterations: int | None = None) -> None:
    """Continuously poll for and execute background jobs."""
    worker_id = f"worker-daemon-{os.getpid()}"
    logger.info("Starting Evidra background worker %s", worker_id)
    iterations = 0

    while True:
        try:
            executed = poll_and_execute_next(worker_id)
            if not executed:
                time.sleep(poll_interval)
        except Exception:
            logger.exception("Error in worker loop")
            time.sleep(poll_interval)

        iterations += 1
        if max_iterations is not None and iterations >= max_iterations:
            break


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    run_worker_daemon()
