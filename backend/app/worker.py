"""Background worker process executing durable asynchronous jobs."""
import logging
import os
import threading
import time
from uuid import uuid4

from sqlalchemy.orm import Session

from app.contracts.enums import JobKind, JobState
from app.db.session import SessionLocal, get_db
from app.services.imports import run_import_job
from app.services.jobs import acquire_next_job, get_job_by_id

logger = logging.getLogger(__name__)


def _get_worker_session(db: Session | None = None) -> tuple[Session, bool]:
    if db is not None:
        return db, False
    from app.main import app
    if get_db in app.dependency_overrides:
        gen = app.dependency_overrides[get_db]()
        return next(gen), False
    return SessionLocal(), True


def run_corpus_pipeline_job(db: Session, job) -> None:
    """Execute LangGraph review pipeline for a background job."""
    import json

    from app.contracts.models import ErrorEnvelope
    from app.services.jobs import fail_job, update_job_progress
    from app.workflows.pipeline import run_review_pipeline

    try:
        update_job_progress(db, job.id, processed_items=0, total_items=1, stage="processing")
        payload = {}
        if getattr(job, "payload_json", None):
            payload = json.loads(job.payload_json)
        crit_id = payload.get("criteria_version_id")
        result = run_review_pipeline(
            workspace_id=job.workspace_id,
            job_id=job.id,
            criteria_version_id=crit_id,
            db=db,
        )
        revision_id = result.get("corpus_revision_id")
        if revision_id and not result.get("error"):
            # Evidence claims, radar and challenges are made here, once, so no GET has to write them
            from app.services.derived import precompute_review_artifacts

            try:
                made = precompute_review_artifacts(db, job.workspace_id, revision_id)
                logger.info("Prepared evidence for job %s: %s", job.id, made)
            except Exception:  # noqa: BLE001 - the papers are screened even if this step fails
                db.rollback()
                logger.exception("Could not prepare evidence artifacts for job %s", job.id)
        if result.get("error"):
            fail_job(db, job.id, ErrorEnvelope(code="WORKFLOW_ERROR", message=result["error"]))
        elif result.get("__interrupt__"):
            job.state = JobState.WAITING_HUMAN.value
            job.stage = "waiting_human_review"
            db.commit()
        else:
            update_job_progress(db, job.id, processed_items=1, total_items=1, stage="done", state=JobState.SUCCEEDED)
    except Exception as e:
        logger.exception("Failed to execute corpus review graph for job %s", job.id)
        fail_job(db, job.id, ErrorEnvelope(code="EXECUTION_ERROR", message=str(e)))


def process_single_job(job_id: str, db: Session | None = None) -> None:
    """Execute a specific job synchronously within a worker session."""
    session, should_close = _get_worker_session(db)
    try:
        job = get_job_by_id(session, job_id)
        if job.kind == JobKind.IMPORT_RECORDS.value:
            run_import_job(session, job)
        elif job.kind in (JobKind.DEDUP.value, JobKind.SCREEN.value, JobKind.PICO.value):
            run_corpus_pipeline_job(session, job)
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
        elif job.kind in (JobKind.DEDUP.value, JobKind.SCREEN.value, JobKind.PICO.value):
            run_corpus_pipeline_job(session, job)
        return True
    finally:
        if should_close:
            session.close()


def run_worker_daemon(
    poll_interval: float = 1.0,
    max_iterations: int | None = None,
    stop_event: threading.Event | None = None,
) -> None:
    """Continuously poll for and execute background jobs until stopped."""
    worker_id = f"worker-daemon-{os.getpid()}"
    logger.info("Starting Evidra background worker %s", worker_id)
    iterations = 0

    while not (stop_event and stop_event.is_set()):
        try:
            executed = poll_and_execute_next(worker_id)
            if not executed:
                if stop_event:
                    stop_event.wait(poll_interval)
                else:
                    time.sleep(poll_interval)
        except Exception:
            logger.exception("Error in worker loop")
            if stop_event:
                stop_event.wait(poll_interval)
            else:
                time.sleep(poll_interval)

        iterations += 1
        if max_iterations is not None and iterations >= max_iterations:
            break

    logger.info("Evidra background worker %s stopped", worker_id)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    run_worker_daemon()
