"""Read models that let the app pick up exactly where a reviewer left off after a reload.

Dashboard summaries, the latest saved query, its search counts (with the reviewer's
import ticks) and recent jobs all come straight from the database.
"""
from __future__ import annotations

import json

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.contracts.enums import EffectiveDecisionState, JobKind
from app.contracts.models import (
    DashboardReviewSummary,
    JobResponse,
    QueryASTNode,
    QueryVersionResponse,
    SearchExecutionResponse,
)
from app.db.models import (
    CorpusRevisionModel,
    CriteriaVersionModel,
    GroupSnapshotModel,
    JobModel,
    QueryVersionModel,
    ReviewEventModel,
    SearchExecutionModel,
    WorkspaceModel,
)
from app.services.corpus import project_group_decisions_bulk
from app.services.jobs import to_job_response


def query_version_response(model: QueryVersionModel) -> QueryVersionResponse:
    return QueryVersionResponse(
        id=model.id,
        workspace_id=model.workspace_id,
        parent_id=model.parent_id,
        sequence=model.sequence,
        ast=QueryASTNode.model_validate_json(model.ast_json),
        start_date=model.start_date,
        end_date=model.end_date,
        sources=json.loads(model.sources_json),
        criteria_version_id=model.criteria_version_id,
        content_hash=model.content_hash,
        change_description=model.change_description,
        restored_from_version_id=model.restored_from_version_id,
        created_at=model.created_at,
    )


def latest_query_version(db: Session, workspace_id: str) -> QueryVersionResponse:
    row = (
        db.query(QueryVersionModel)
        .filter_by(workspace_id=workspace_id)
        .order_by(QueryVersionModel.sequence.desc())
        .first()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No saved search yet")
    return query_version_response(row)


def list_executions(db: Session, workspace_id: str, query_version_id: str | None) -> list[SearchExecutionResponse]:
    """Search counts for one query version (default: the latest), newest first."""
    if query_version_id is None:
        latest = (
            db.query(QueryVersionModel.id)
            .filter_by(workspace_id=workspace_id)
            .order_by(QueryVersionModel.sequence.desc())
            .first()
        )
        if latest is None:
            return []
        query_version_id = latest[0]
    rows = (
        db.query(SearchExecutionModel)
        .join(QueryVersionModel, QueryVersionModel.id == SearchExecutionModel.query_version_id)
        .filter(
            QueryVersionModel.workspace_id == workspace_id,
            SearchExecutionModel.query_version_id == query_version_id,
        )
        .order_by(SearchExecutionModel.counted_at.desc())
        .all()
    )
    return [SearchExecutionResponse.model_validate(r) for r in rows]


def set_execution_selection(db: Session, execution_id: str, selected: bool) -> SearchExecutionResponse:
    row = db.get(SearchExecutionModel, execution_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Search count not found")
    if selected and row.hit_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This count found nothing, so there is nothing to import from it.",
        )
    row.selected_for_import = selected
    db.commit()
    return SearchExecutionResponse.model_validate(row)


def list_jobs(db: Session, workspace_id: str, kind: JobKind | None, limit: int) -> list[JobResponse]:
    q = db.query(JobModel).filter_by(workspace_id=workspace_id)
    if kind is not None:
        q = q.filter_by(kind=kind.value)
    rows = q.order_by(JobModel.created_at.desc()).limit(limit).all()
    return [to_job_response(r) for r in rows]


def dashboard_summaries(db: Session, workspaces: list[WorkspaceModel]) -> list[DashboardReviewSummary]:
    """Screening progress for each review, in a handful of queries per review."""
    summaries: list[DashboardReviewSummary] = []
    ws_ids = [w.id for w in workspaces]
    questions: dict[str, str] = {}
    if ws_ids:
        latest_seq = (
            db.query(CriteriaVersionModel.workspace_id, func.max(CriteriaVersionModel.sequence))
            .filter(CriteriaVersionModel.workspace_id.in_(ws_ids))
            .group_by(CriteriaVersionModel.workspace_id)
            .all()
        )
        for ws_id, seq in latest_seq:
            row = db.query(CriteriaVersionModel.question).filter_by(workspace_id=ws_id, sequence=seq).first()
            if row:
                questions[ws_id] = row[0]

    for ws in workspaces:
        last_activity = ws.updated_at or ws.created_at
        for model in (ReviewEventModel, JobModel):
            latest = db.query(func.max(model.created_at)).filter(model.workspace_id == ws.id).scalar()
            if latest and latest > last_activity:
                last_activity = latest

        summary = DashboardReviewSummary(
            id=ws.id,
            title=ws.title,
            question=questions.get(ws.id),
            created_at=ws.created_at,
            last_activity_at=last_activity,
        )
        revision = db.get(CorpusRevisionModel, ws.current_revision_id) if ws.current_revision_id else None
        if revision is not None:
            group_ids = [
                gid
                for (gid,) in db.query(GroupSnapshotModel.group_id).filter_by(corpus_revision_id=revision.id).all()
            ]
            decisions = project_group_decisions_bulk(db, group_ids, revision.id)
            summary.record_count = revision.record_count
            summary.group_count = len(group_ids)
            for state, human_event, _screen, _conflict in decisions.values():
                if state == EffectiveDecisionState.INCLUDE:
                    summary.included += 1
                elif state == EffectiveDecisionState.EXCLUDE:
                    summary.excluded += 1
                elif state == EffectiveDecisionState.MAYBE:
                    summary.maybe += 1
                elif state == EffectiveDecisionState.CONFLICT:
                    summary.conflicts += 1
                if human_event is not None:
                    summary.reviewed_by_human += 1
            summary.awaiting_review = summary.group_count - summary.reviewed_by_human
        summaries.append(summary)
    return summaries
