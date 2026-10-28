"""Service layer executing ML prioritization, caching, provenance, and group-level projection."""
from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.contracts.models import (
    MLRankedItem,
    MLRankingRequest,
    MLRankingResponse,
)
from app.db.models import (
    CorpusRevisionModel,
    CriteriaVersionModel,
    GroupSnapshotModel,
    MachineResultModel,
    RecordRevisionModel,
    RunLogModel,
    WorkspaceModel,
)
from app.ml_feature.ranker import MLRanker, load_ranker
from app.ml_feature.types import RankingContext, RecordInput
from app.services.corpus import project_effective_group_decision

logger = logging.getLogger(__name__)


def resolve_artifact_directory(override_dir: Path | str | None = None) -> Path:
    """Resolve directory containing verified model.joblib and manifest.json."""
    if override_dir is not None:
        return Path(override_dir)

    candidates = [
        Path("evals/ml_c/artifact"),
        Path("../evals/ml_c/artifact"),
        Path("./backend/../evals/ml_c/artifact"),
        Path(__file__).resolve().parent.parent.parent.parent / "evals" / "ml_c" / "artifact",
    ]
    for c in candidates:
        if (c / "manifest.json").exists() and (c / "model.joblib").exists():
            return c

    # Fallback to standard path
    return Path("evals/ml_c/artifact")


def execute_ml_ranking(
    db: Session,
    workspace_id: str,
    revision_id: str,
    request: MLRankingRequest | None = None,
    artifact_dir: Path | str | None = None,
) -> MLRankingResponse:
    """Compute, cache, or retrieve prioritized screening order for a corpus revision.

    Strict Invariants:
    1. Read-only authorization: rejects unknown workspace or revision with 404.
    2. Zero human decision mutations: never alters ReviewEventModel.
    3. Reproducible tamper-protected artifact: rejects modified models.
    4. Safe degradation: missing or invalid artifacts return status='UNAVAILABLE' with reason,
       allowing baseline rules/manual screening to continue uninterrupted.
    5. Idempotent caching: repeats return identical ranking from MachineResultModel.
    """
    req = request or MLRankingRequest()

    # 1. Workspace membership verification
    ws = db.query(WorkspaceModel).filter_by(id=workspace_id).first()
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found",
        )

    # 2. Corpus revision verification
    corpus_rev = (
        db.query(CorpusRevisionModel)
        .filter_by(id=revision_id, workspace_id=workspace_id)
        .first()
    )
    if not corpus_rev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Corpus revision '{revision_id}' not found in workspace '{workspace_id}'",
        )

    # 3. Criteria & Question resolution
    criteria = db.query(CriteriaVersionModel).filter_by(id=corpus_rev.criteria_version_id).first()
    review_question = req.review_question or (criteria.question if criteria else "")

    # 4. Retrieve group snapshots and primary records
    snapshots = (
        db.query(GroupSnapshotModel)
        .filter_by(corpus_revision_id=revision_id)
        .all()
    )

    if not snapshots:
        return MLRankingResponse(
            workspace_id=workspace_id,
            revision_id=revision_id,
            criteria_version_id=corpus_rev.criteria_version_id,
            model_version="none",
            scope=review_question,
            status="EMPTY",
            reason="Corpus revision contains no literature records",
            total_records=0,
            scored_count=0,
            items=[],
            computed_at=datetime.now(UTC).isoformat(),
            duration_ms=0,
        )

    if len(snapshots) > 50000:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Corpus revision exceeds 50,000 record threshold for synchronous ranking",
        )

    # 5. Compute stable input fingerprint for caching
    fingerprint_seed = f"{workspace_id}:{revision_id}:{criteria.content_hash if criteria else 'none'}:{len(snapshots)}"
    input_fingerprint = hashlib.sha256(fingerprint_seed.encode("utf-8")).hexdigest()

    # 6. Check MachineResultModel cache (unless force_recompute=True)
    if not req.force_recompute:
        cached_results = (
            db.query(MachineResultModel)
            .filter_by(
                corpus_revision_id=revision_id,
                stage="ml_ranking",
            )
            .all()
        )
        # Verify matching count and matching fingerprint prefix
        if len(cached_results) == len(snapshots) and all(
            cr.input_fingerprint.startswith(input_fingerprint[:16]) for cr in cached_results
        ):
            # Cache hit: parse stored JSON payloads and apply pagination
            cached_items: list[MLRankedItem] = []
            for cr in cached_results:
                try:
                    payload = json.loads(cr.output_json)
                    cached_items.append(MLRankedItem(**payload))
                except (json.JSONDecodeError, TypeError, ValueError) as ex:
                    logger.warning("Failed parsing cached ML item %s: %s", cr.id, ex)

            # Sort by rank
            cached_items.sort(key=lambda it: it.rank)
            paginated_items = cached_items[req.offset : req.offset + req.limit]

            return MLRankingResponse(
                workspace_id=workspace_id,
                revision_id=revision_id,
                criteria_version_id=corpus_rev.criteria_version_id,
                model_version=cached_results[0].method_version if cached_results else "cached",
                scope=review_question,
                status="CACHED",
                reason="Retrieved from validated machine results cache",
                total_records=len(cached_items),
                scored_count=sum(1 for it in cached_items if it.state == "SCORED"),
                items=paginated_items,
                computed_at=cached_results[0].created_at.isoformat() if cached_results else datetime.now(UTC).isoformat(),
                duration_ms=1,
            )

    # 7. Load verified ML ranker artifact
    art_path = resolve_artifact_directory(artifact_dir)
    ranker: MLRanker | None = None
    try:
        ranker = load_ranker(art_path)
    except (FileNotFoundError, ValueError, OSError, RuntimeError) as exc:
        logger.error("ML ranker artifact failed verification at %s: %s", art_path, exc)
        # Log failure into run logs
        trace_id = str(uuid4())
        run_log = RunLogModel(
            workspace_id=workspace_id,
            stage="ml_ranking",
            status="UNAVAILABLE",
            error_code=exc.__class__.__name__,
            input_hash=input_fingerprint,
            trace_id=trace_id,
            duration_ms=0,
        )
        db.add(run_log)
        db.commit()

        return MLRankingResponse(
            workspace_id=workspace_id,
            revision_id=revision_id,
            criteria_version_id=corpus_rev.criteria_version_id,
            model_version="unavailable",
            scope=review_question,
            status="UNAVAILABLE",
            reason=f"Model artifact unavailable or integrity verification failed: {exc}",
            total_records=len(snapshots),
            scored_count=0,
            items=[],
            computed_at=datetime.now(UTC).isoformat(),
            duration_ms=0,
        )

    # 8. Assemble records for ML processing
    t0 = time.perf_counter()
    record_inputs: list[RecordInput] = []
    group_map: dict[str, str] = {}  # record_id -> group_id
    effective_status_map: dict[str, str] = {}  # group_id -> status str

    for snap in snapshots:
        group_id = snap.group_id
        rep_rev = db.query(RecordRevisionModel).filter_by(id=snap.representative_revision_id).first()
        if not rep_rev:
            continue

        group_map[rep_rev.id] = group_id
        eff_state, _, _, _ = project_effective_group_decision(db, group_id=group_id, revision_id=revision_id)
        effective_status_map[group_id] = eff_state.value

        record_inputs.append(
            RecordInput(
                id=rep_rev.id,
                title=rep_rev.title or "",
                abstract_text=rep_rev.abstract_text,
                group_id=group_id,
            )
        )

    # 9. Perform pure CPU model inference
    target_scope = ranker.manifest.scope
    ranking_ctx = RankingContext(
        review_question=target_scope,  # Bind to verified artifact scope
        criteria_version_id=corpus_rev.criteria_version_id,
    )
    ranking_batch = ranker.rank_records(record_inputs, ranking_ctx)
    duration_ms = max(1, int((time.perf_counter() - t0) * 1000))

    # 10. Map ranked items with priority labels and effective decisions
    items_to_persist: list[MLRankedItem] = []
    input_lookup = {r.id: r for r in record_inputs}

    for item in ranking_batch.items:
        grp_id = group_map.get(item.record_id)
        rec = input_lookup.get(item.record_id)
        eff_status = effective_status_map.get(grp_id or "", "unscreened")

        # Label priority tiers
        if item.state != "SCORED":
            priority = "UNSCORED"
        elif item.score >= 0.70:
            priority = "HIGH"
        elif item.score >= 0.40:
            priority = "MEDIUM"
        else:
            priority = "LOW"

        ranked_dto = MLRankedItem(
            record_id=item.record_id,
            group_id=grp_id,
            title=rec.title if rec else "",
            abstract_text=rec.abstract_text if rec else None,
            score=item.score,
            rank=item.rank,
            state=item.state,
            reason=item.reason,
            priority_label=priority,
            effective_status=eff_status,
        )
        items_to_persist.append(ranked_dto)

    # 11. Atomic persistence into MachineResultModel and RunLogModel
    try:
        # Clear prior results for this revision stage
        db.query(MachineResultModel).filter_by(
            corpus_revision_id=revision_id,
            stage="ml_ranking",
        ).delete()

        for it in items_to_persist:
            item_fp = f"{input_fingerprint[:16]}:{hashlib.sha256(it.record_id.encode()).hexdigest()[:47]}"
            mr = MachineResultModel(
                corpus_revision_id=revision_id,
                group_id=it.group_id or it.record_id,
                record_revision_id=it.record_id,
                stage="ml_ranking",
                input_fingerprint=item_fp,
                method_version=ranker.manifest.artifact_version,
                output_json=it.model_dump_json(),
            )
            db.add(mr)

        trace_id = str(uuid4())
        run_log = RunLogModel(
            workspace_id=workspace_id,
            stage="ml_ranking",
            status="SUCCESS",
            input_hash=input_fingerprint,
            output_hash=hashlib.sha256(str(ranking_batch.scored_count).encode()).hexdigest(),
            trace_id=trace_id,
            duration_ms=duration_ms,
        )
        db.add(run_log)
        db.commit()
    except (SQLAlchemyError, OSError, ValueError) as ex:
        db.rollback()
        logger.error("Failed persisting machine results: %s", ex)

    # 12. Paginated response
    paginated_items = items_to_persist[req.offset : req.offset + req.limit]

    return MLRankingResponse(
        workspace_id=workspace_id,
        revision_id=revision_id,
        criteria_version_id=corpus_rev.criteria_version_id,
        model_version=ranker.manifest.artifact_version,
        scope=ranker.manifest.scope,
        status="COMPLETED",
        reason="Prioritization computed via verified scikit-learn pipeline",
        total_records=len(items_to_persist),
        scored_count=ranking_batch.scored_count,
        items=paginated_items,
        computed_at=datetime.now(UTC).isoformat(),
        duration_ms=duration_ms,
    )
