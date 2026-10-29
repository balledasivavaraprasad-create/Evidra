"""Review ownership: every API call may only touch reviews the signed-in user owns.

Applied once, app-wide, as a FastAPI dependency. It looks at the route's path and
query parameters, resolves each recognised ID (group, job, revision, ...) to the review
(workspace) it belongs to, and requires that every one of them is a review the caller
owns. Unknown or foreign IDs get 404, never 403, so other people's review IDs can't be
probed. In AUTH_MODE=local nothing is enforced.
"""
from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth import accounts_enabled, current_user_id
from app.db.models import (
    CorpusRevisionModel,
    DuplicateMergeEventModel,
    ExportModel,
    JobModel,
    PaperGroupModel,
    PrismaSnapshotModel,
    QueryVersionModel,
    ReviewConflictModel,
    SearchExecutionModel,
    WorkspaceModel,
)
from app.db.session import get_db


def _group_ws(db: Session, value: str) -> str | None:
    row = db.query(PaperGroupModel.workspace_id).filter_by(id=value).first()
    return row[0] if row else None


def _revision_ws(db: Session, value: str) -> str | None:
    row = db.query(CorpusRevisionModel.workspace_id).filter_by(id=value).first()
    return row[0] if row else None


def _query_version_ws(db: Session, value: str) -> str | None:
    row = db.query(QueryVersionModel.workspace_id).filter_by(id=value).first()
    return row[0] if row else None


def _job_ws(db: Session, value: str) -> str | None:
    row = db.query(JobModel.workspace_id).filter_by(id=value).first()
    return row[0] if row else None


def _export_ws(db: Session, value: str) -> str | None:
    row = db.query(ExportModel.workspace_id).filter_by(id=value).first()
    return row[0] if row else None


def _conflict_ws(db: Session, value: str) -> str | None:
    row = (
        db.query(PaperGroupModel.workspace_id)
        .join(ReviewConflictModel, ReviewConflictModel.group_id == PaperGroupModel.id)
        .filter(ReviewConflictModel.id == value)
        .first()
    )
    return row[0] if row else None


def _merge_event_ws(db: Session, value: str) -> str | None:
    row = db.query(DuplicateMergeEventModel.workspace_id).filter_by(id=value).first()
    return row[0] if row else None


def _snapshot_ws(db: Session, value: str) -> str | None:
    row = db.query(CorpusRevisionModel.workspace_id).filter_by(id=value).first()
    if row:
        return row[0]
    row = db.query(PrismaSnapshotModel.workspace_id).filter_by(id=value).first()
    return row[0] if row else None


def execution_workspace_id(db: Session, execution_id: str) -> str | None:
    row = (
        db.query(QueryVersionModel.workspace_id)
        .join(SearchExecutionModel, SearchExecutionModel.query_version_id == QueryVersionModel.id)
        .filter(SearchExecutionModel.id == execution_id)
        .first()
    )
    return row[0] if row else None


# Parameter name -> how to find the review it belongs to. "workspace_id" is checked directly.
RESOLVERS: dict[str, Callable[[Session, str], str | None]] = {
    "group_id": _group_ws,
    "revision_id": _revision_ws,
    "base_revision_id": _revision_ws,
    "query_id": _query_version_ws,
    "version_id": _query_version_ws,
    "target_version_id": _query_version_ws,
    "base_version_id": _query_version_ws,
    "job_id": _job_ws,
    "export_id": _export_ws,
    "conflict_id": _conflict_ws,
    "event_id": _merge_event_ws,
    "execution_id": execution_workspace_id,
    "snapshot_id": _snapshot_ws,
    "prisma_snapshot_id": _snapshot_ws,
}


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def user_owns_workspace(db: Session, user_id: str | None, workspace_id: str) -> bool:
    if not accounts_enabled():
        return db.query(WorkspaceModel.id).filter_by(id=workspace_id).first() is not None
    if not user_id:
        return False
    return (
        db.query(WorkspaceModel.id).filter_by(id=workspace_id, owner_user_id=user_id).first() is not None
    )


def require_workspace_owner(db: Session, user_id: str | None, workspace_id: str) -> None:
    if not user_owns_workspace(db, user_id, workspace_id):
        raise _not_found()


def enforce_review_access(request: Request, db: Session = Depends(get_db)) -> None:  # noqa: B008
    """App-wide dependency: 404 unless every review ID in the path/query belongs to the caller."""
    if not accounts_enabled():
        return
    path = request.url.path
    if not path.startswith("/api/") or path.startswith("/api/v1/auth/"):
        return

    params: dict[str, str] = {**request.query_params, **request.path_params}
    user_id = current_user_id(request)
    workspace_ids: set[str] = set()

    if "workspace_id" in params:
        workspace_ids.add(params["workspace_id"])
    for name, resolver in RESOLVERS.items():
        value = params.get(name)
        if not value:
            continue
        ws_id = resolver(db, value)
        if ws_id is None:
            raise _not_found()
        workspace_ids.add(ws_id)

    for ws_id in workspace_ids:
        require_workspace_owner(db, user_id, ws_id)
    # A child ID from one review combined with another review's workspace_id is also rejected
    if len(workspace_ids) > 1:
        raise _not_found()
