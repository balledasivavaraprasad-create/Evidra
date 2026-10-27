"""Background job lifecycle, durable leasing, and progress tracking service."""
import contextlib
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.contracts.enums import JobKind, JobState
from app.contracts.models import ErrorEnvelope, JobResponse
from app.db.models import JobModel, WorkspaceModel


def create_job(
    db: Session,
    workspace_id: str,
    kind: JobKind,
    request_key: str,
    payload: dict,
    total_items: int | None = None,
) -> JobModel:
    """Atomically create a queued job with idempotency protection."""
    # 1. Authorize workspace
    ws = db.query(WorkspaceModel).filter_by(id=workspace_id).first()
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found",
        )

    # 2. Check for duplicate request key
    payload_hash = json.dumps(payload, sort_keys=True)
    existing = db.query(JobModel).filter_by(workspace_id=workspace_id, request_key=request_key).first()
    if existing:
        if existing.payload_hash == payload_hash:
            return existing
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Request key was already used with different parameters",
        )

    job = JobModel(
        id=str(uuid4()),
        workspace_id=workspace_id,
        kind=kind.value,
        request_key=request_key,
        payload_hash=payload_hash,
        state=JobState.QUEUED.value,
        progress=0.0,
        stage="queued",
        total_items=total_items,
        processed_items=0,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job_by_id(db: Session, job_id: str) -> JobModel:
    """Retrieve job by UUID or raise 404."""
    job = db.query(JobModel).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found",
        )
    return job


def to_job_response(job: JobModel) -> JobResponse:
    """Convert SQLAlchemy JobModel to Pydantic JobResponse."""
    error = None
    if job.error_json:
        with contextlib.suppress(Exception):
            error = ErrorEnvelope.model_validate_json(job.error_json)

    return JobResponse(
        id=job.id,
        workspace_id=job.workspace_id,
        kind=JobKind(job.kind),
        request_key=job.request_key,
        state=JobState(job.state),
        progress=job.progress,
        stage=job.stage,
        total_items=job.total_items,
        processed_items=job.processed_items,
        error=error,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def update_job_progress(
    db: Session,
    job_id: str,
    processed_items: int,
    total_items: int | None = None,
    stage: str | None = None,
    state: JobState = JobState.RUNNING,
) -> None:
    """Update job progress and stage safely."""
    job = get_job_by_id(db, job_id)
    job.processed_items = processed_items
    if total_items is not None:
        job.total_items = total_items
    if stage:
        job.stage = stage
    job.state = state.value
    if job.total_items and job.total_items > 0:
        job.progress = min(1.0, float(job.processed_items) / float(job.total_items))
    db.commit()


def fail_job(
    db: Session,
    job_id: str,
    error: ErrorEnvelope,
    partial: bool = False,
) -> None:
    """Mark job as failed or partial with structured error details."""
    job = get_job_by_id(db, job_id)
    job.state = JobState.PARTIAL.value if partial else JobState.FAILED.value
    job.error_json = error.model_dump_json()
    job.stage = "partial_interruption" if partial else "failed"
    db.commit()


def cancel_job(db: Session, job_id: str) -> JobModel:
    """Cancel a running or queued job."""
    job = get_job_by_id(db, job_id)
    if job.state in (JobState.SUCCEEDED.value, JobState.FAILED.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job in terminal state '{job.state}'",
        )
    job.state = JobState.CANCELLED.value
    job.stage = "cancelled"
    db.commit()
    db.refresh(job)
    return job


def acquire_next_job(db: Session, worker_id: str, lease_seconds: int = 60) -> JobModel | None:
    """Atomically claim the next queued or expired-lease job."""
    now = datetime.now(UTC)
    # Find queued or abandoned jobs
    job = (
        db.query(JobModel)
        .filter(
            (JobModel.state == JobState.QUEUED.value)
            | (
                (JobModel.state == JobState.RUNNING.value)
                & (JobModel.lease_until < now)
            )
        )
        .order_by(JobModel.created_at.asc())
        .with_for_update(skip_locked=True)
        .first()
    )

    if job:
        job.state = JobState.RUNNING.value
        job.lease_owner = worker_id
        job.lease_until = now + timedelta(seconds=lease_seconds)
        job.stage = "started"
        db.commit()
        db.refresh(job)
    return job
