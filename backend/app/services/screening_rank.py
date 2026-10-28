"""Service exposing classical ML screening ranking for workbench prioritization (B05/D06)."""
from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.contracts.enums import CorpusRevisionState
from app.contracts.models import (
    RankedGroupItem,
    ScreeningRankRequest,
    ScreeningRankResponse,
)
from app.db.models import (
    CorpusRevisionModel,
    GroupSnapshotModel,
    RecordRevisionModel,
    WorkspaceModel,
)
from app.screening.ml.ranker import MLScreeningRanker
from app.screening.ml.types import MLRankingStatus, MLRecordInput
from app.settings import settings


def rank_screening_groups(
    db: Session,
    workspace_id: str,
    request: ScreeningRankRequest,
    artifact_dir: Path | None = None,
) -> ScreeningRankResponse:
    """Compute or retrieve prioritized screening ranking for paper groups in a corpus revision.

    Never automatically excludes or includes papers; outputs assistive priority order.
    """
    ws = db.query(WorkspaceModel).filter_by(id=workspace_id).first()
    if not ws:
        return ScreeningRankResponse(
            workspace_id=workspace_id,
            revision_id=request.revision_id or "",
            status=MLRankingStatus.UNAVAILABLE_INSUFFICIENT_DATA.value,
            reason=f"Workspace '{workspace_id}' not found",
        )

    # Resolve revision
    if request.revision_id:
        revision = (
            db.query(CorpusRevisionModel)
            .filter_by(id=request.revision_id, workspace_id=workspace_id)
            .first()
        )
    else:
        revision = (
            db.query(CorpusRevisionModel)
            .filter_by(workspace_id=workspace_id, state=CorpusRevisionState.PUBLISHED.value)
            .order_by(CorpusRevisionModel.created_at.desc())
            .first()
        )
        if not revision:
            revision = (
                db.query(CorpusRevisionModel)
                .filter_by(workspace_id=workspace_id)
                .order_by(CorpusRevisionModel.created_at.desc())
                .first()
            )

    if not revision:
        return ScreeningRankResponse(
            workspace_id=workspace_id,
            revision_id=request.revision_id or "",
            status=MLRankingStatus.UNAVAILABLE_INSUFFICIENT_DATA.value,
            reason="No corpus revision found in workspace",
        )

    # Query group snapshots in revision
    snapshots = (
        db.query(GroupSnapshotModel)
        .filter_by(corpus_revision_id=revision.id)
        .all()
    )
    if not snapshots:
        return ScreeningRankResponse(
            workspace_id=workspace_id,
            revision_id=revision.id,
            status=MLRankingStatus.UNAVAILABLE_INSUFFICIENT_DATA.value,
            reason="No paper groups present in revision",
        )

    # Fetch primary record title and abstract for each group from snapshot
    inputs: list[MLRecordInput] = []
    for snap in snapshots:
        rec = (
            db.query(RecordRevisionModel)
            .filter_by(id=snap.representative_revision_id)
            .first()
        )
        title = rec.title or "" if rec else ""
        abstract = rec.abstract or "" if rec else ""
        inputs.append(MLRecordInput(id=snap.group_id, title=title, abstract=abstract))

    # Initialize ML ranker
    models_dir = artifact_dir or (settings.data_dir / "models")
    ranker = MLScreeningRanker(artifact_dir=models_dir)
    ml_result = ranker.rank_records(inputs)

    # Convert to API response
    ranked_items: list[RankedGroupItem] = [
        RankedGroupItem(
            group_id=r.record_id,
            score=round(r.score, 4),
            rank=r.rank,
        )
        for r in ml_result.ranked_records[: request.limit]
    ]

    return ScreeningRankResponse(
        workspace_id=workspace_id,
        revision_id=revision.id,
        status=ml_result.status.value,
        model_version=ml_result.model_version,
        ranked_groups=ranked_items,
        reason=ml_result.reason,
    )
