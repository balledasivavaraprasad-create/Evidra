"""Durable literature record import service and source persistence."""
import json
import logging
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.contracts.enums import JobKind, JobState, SourceNamespace
from app.contracts.models import (
    ErrorEnvelope,
    ImportJobCreate,
    JobResponse,
    RecordRevisionResponse,
)
from app.db.models import (
    JobModel,
    QueryMembershipModel,
    RecordRevisionModel,
    SearchExecutionModel,
    SourceRecordModel,
    WorkspaceModel,
)
from app.services.jobs import create_job, fail_job, to_job_response, update_job_progress
from app.sources.europepmc import EuropePMCAdapter
from app.sources.pubmed import PubMedAdapter

logger = logging.getLogger(__name__)


def trigger_import(
    db: Session,
    workspace_id: str,
    payload: ImportJobCreate,
) -> JobResponse:
    """Validate approved search executions and queue durable import job."""
    ws = db.query(WorkspaceModel).filter_by(id=workspace_id).first()
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found",
        )

    # Validate that all search executions exist and belong to this workspace
    for exec_id in payload.search_execution_ids:
        exec_row = db.query(SearchExecutionModel).filter_by(id=exec_id).first()
        if not exec_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Search execution '{exec_id}' not found",
            )
        # Check query version belongs to workspace
        if exec_row.query_version.workspace_id != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Search execution '{exec_id}' belongs to another workspace",
            )

    job_payload = {
        "search_execution_ids": payload.search_execution_ids,
        "cap": payload.cap,
    }

    job = create_job(
        db=db,
        workspace_id=workspace_id,
        kind=JobKind.IMPORT_RECORDS,
        request_key=payload.idempotency_key,
        payload=job_payload,
        total_items=payload.cap or 200,
    )

    return to_job_response(job)


def persist_record_revision(
    db: Session,
    workspace_id: str,
    search_execution_id: str,
    record: RecordRevisionResponse,
) -> None:
    """Upsert source identity and revision, recording query membership atomically."""
    # 1. Upsert SourceRecord (identity)
    source_rec = (
        db.query(SourceRecordModel)
        .filter_by(
            workspace_id=workspace_id,
            source=record.source.value,
            source_namespace=record.source_namespace,
            external_id=record.external_id,
        )
        .first()
    )

    if not source_rec:
        source_rec = SourceRecordModel(
            id=str(uuid4()),
            workspace_id=workspace_id,
            source=record.source.value,
            source_namespace=record.source_namespace,
            external_id=record.external_id,
        )
        db.add(source_rec)
        db.flush()

    # 2. Check if identical content hash revision exists for this source record
    revision = (
        db.query(RecordRevisionModel)
        .filter_by(
            source_record_id=source_rec.id,
            content_hash=record.content_hash,
        )
        .first()
    )

    if not revision:
        sections_json = json.dumps([s.model_dump() for s in record.structured_sections]) if record.structured_sections else None
        revision = RecordRevisionModel(
            id=str(uuid4()),
            source_record_id=source_rec.id,
            content_hash=record.content_hash,
            title=record.title,
            abstract_text=record.abstract_text,
            structured_sections_json=sections_json,
            authors_json=json.dumps(record.authors),
            year=record.year,
            journal=record.journal,
            pages=record.pages,
            language_json=json.dumps(record.language),
            publication_types_json=json.dumps(record.publication_types),
            doi=record.doi,
            pmid=record.pmid,
            metadata_json=json.dumps(record.metadata_json),
            fetched_at=record.fetched_at,
        )
        db.add(revision)
        db.flush()

    # 3. Associate query membership
    membership = (
        db.query(QueryMembershipModel)
        .filter_by(
            search_execution_id=search_execution_id,
            source_record_id=source_rec.id,
        )
        .first()
    )

    if not membership:
        membership = QueryMembershipModel(
            search_execution_id=search_execution_id,
            source_record_id=source_rec.id,
            record_revision_id=revision.id,
        )
        db.add(membership)
        db.flush()


def run_import_job(db: Session, job: JobModel) -> None:
    """Execute import job across approved search executions."""
    try:
        payload_data = json.loads(job.payload_json or job.payload_hash)
        execution_ids = payload_data.get("search_execution_ids", [])
        cap = payload_data.get("cap", 200)

        pubmed_adapter = PubMedAdapter()
        epmc_adapter = EuropePMCAdapter()

        total_imported = 0

        for exec_id in execution_ids:
            exec_row = db.query(SearchExecutionModel).filter_by(id=exec_id).first()
            if not exec_row:
                continue

            # Check if job was cancelled
            db.refresh(job)
            if job.state == JobState.CANCELLED.value:
                return

            if exec_row.source == SourceNamespace.PUBMED.value:
                pmids = pubmed_adapter.fetch_ids_for_execution(
                    exact_query=exec_row.exact_query,
                    retmax=cap - total_imported,
                )

                # Batch in 50s
                for i in range(0, len(pmids), 50):
                    db.refresh(job)
                    if job.state == JobState.CANCELLED.value:
                        return

                    batch_pmids = pmids[i : i + 50]
                    records = pubmed_adapter.fetch_records_by_pmids(batch_pmids)

                    # Short DB transaction per batch
                    for rec in records:
                        persist_record_revision(db, job.workspace_id, exec_id, rec)
                        total_imported += 1

                    db.commit()
                    update_job_progress(
                        db=db,
                        job_id=job.id,
                        processed_items=total_imported,
                        total_items=len(pmids),
                        stage="importing_pubmed_records",
                    )

            elif exec_row.source == SourceNamespace.EUROPEPMC.value:
                cursor = "*"
                while cursor and total_imported < cap:
                    db.refresh(job)
                    if job.state == JobState.CANCELLED.value:
                        return

                    page_size = min(50, cap - total_imported)
                    records, next_cursor = epmc_adapter.fetch_page(
                        exact_query=exec_row.exact_query,
                        cursor=cursor,
                        page_size=page_size,
                        synonym_expansion=exec_row.synonym_setting,
                    )

                    for rec in records:
                        persist_record_revision(db, job.workspace_id, exec_id, rec)
                        total_imported += 1

                    db.commit()
                    update_job_progress(
                        db=db,
                        job_id=job.id,
                        processed_items=total_imported,
                        total_items=cap,
                        stage="importing_europepmc_records",
                    )
                    cursor = next_cursor

        # Mark succeeded
        update_job_progress(
            db=db,
            job_id=job.id,
            processed_items=total_imported,
            total_items=total_imported if total_imported > 0 else 1,
            stage="completed",
            state=JobState.SUCCEEDED,
        )

    except Exception as exc:
        logger.exception("Import job %s failed", job.id)
        is_partial = job.processed_items > 0
        error_env = ErrorEnvelope(
            code="IMPORT_EXECUTION_ERROR",
            message=str(exc),
            retryable=True,
        )
        fail_job(db, job.id, error_env, partial=is_partial)
