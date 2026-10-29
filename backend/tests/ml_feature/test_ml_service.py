"""Comprehensive unit, integration, and security tests for ML ranking service and API routes (C-ML02)."""
from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.contracts.enums import CorpusRevisionState
from app.contracts.models import (
    MLRankingRequest,
    MLRankingResponse,
)
from app.db.models import (
    CorpusMemberModel,
    CorpusRevisionModel,
    CriteriaVersionModel,
    GroupSnapshotModel,
    MachineResultModel,
    PaperGroupModel,
    RecordRevisionModel,
    ReviewEventModel,
    RunLogModel,
    SourceRecordModel,
    WorkspaceModel,
)
from app.ml_feature.service import execute_ml_ranking
from app.ml_feature.trainer import train_ranker
from app.ml_feature.types import RecordInput, TrainConfig


def test_scope_cannot_be_overridden_by_request(db_session, seeded_workspace, test_artifact_dir):
    ws_id, rev_id = seeded_workspace
    criteria = db_session.query(CriteriaVersionModel).filter_by(workspace_id=ws_id).one()
    original_question = criteria.question
    criteria.question = "A different review about pediatric asthma"
    db_session.commit()
    result = execute_ml_ranking(
        db_session, ws_id, rev_id,
        MLRankingRequest(review_question=original_question), test_artifact_dir,
    )
    assert result.scored_count == 0
    assert result.status == "UNAVAILABLE"


def test_model_digest_invalidates_cached_ranking(db_session, seeded_workspace, test_artifact_dir):
    ws_id, rev_id = seeded_workspace
    first = execute_ml_ranking(db_session, ws_id, rev_id, artifact_dir=test_artifact_dir)
    assert first.status == "COMPLETED"
    # A same-version bundle can change preprocessing/policy, not just estimator bytes.
    manifest_path = test_artifact_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["config"]["priority_policy"] = "updated-policy"
    manifest_path.write_text(json.dumps(manifest))
    result = execute_ml_ranking(db_session, ws_id, rev_id, artifact_dir=test_artifact_dir)
    assert result.status == "COMPLETED"


def test_cached_rankings_refresh_human_status(db_session, seeded_workspace, test_artifact_dir):
    ws_id, rev_id = seeded_workspace
    execute_ml_ranking(db_session, ws_id, rev_id, artifact_dir=test_artifact_dir)
    db_session.add(ReviewEventModel(
        workspace_id=ws_id, group_id="grp-clinical-1", sequence=1,
        event_type="screen_decision", payload_json='{"decision":"exclude"}',
        actor_id="test-user", reason="Verified outside protocol",
    ))
    db_session.commit()
    result = execute_ml_ranking(db_session, ws_id, rev_id, artifact_dir=test_artifact_dir)
    item = next(it for it in result.items if it.group_id == "grp-clinical-1")
    assert result.status == "CACHED"
    assert item.effective_status == "exclude"


def test_criteria_constraint_is_enforced(db_session, seeded_workspace, test_artifact_dir):
    ws_id, rev_id = seeded_workspace
    with pytest.raises(HTTPException) as error:
        execute_ml_ranking(db_session, ws_id, rev_id,
                           MLRankingRequest(criteria_version_id="different"), test_artifact_dir)
    assert error.value.status_code == 409


def test_old_ranking_api_service_handles_real_record_schema(db_session, seeded_workspace, tmp_path):
    from app.contracts.models import ScreeningRankRequest
    from app.services.screening_rank import rank_screening_groups
    ws_id, rev_id = seeded_workspace
    result = rank_screening_groups(db_session, ws_id, ScreeningRankRequest(revision_id=rev_id), tmp_path)
    assert result.status == "unavailable_corrupt_artifact"


def test_corrupt_artifact_cannot_reuse_prior_cache(db_session, seeded_workspace, test_artifact_dir):
    ws_id, rev_id = seeded_workspace
    execute_ml_ranking(db_session, ws_id, rev_id, artifact_dir=test_artifact_dir)
    (test_artifact_dir / "model.joblib").write_bytes(b"not a trusted artifact")
    response = execute_ml_ranking(db_session, ws_id, rev_id, artifact_dir=test_artifact_dir)
    assert response.status == "UNAVAILABLE" and response.scored_count == 0


def test_model_swap_preserves_prior_machine_evidence(db_session, seeded_workspace, test_artifact_dir):
    ws_id, rev_id = seeded_workspace
    execute_ml_ranking(db_session, ws_id, rev_id, artifact_dir=test_artifact_dir)
    original_ids = {row.id for row in db_session.query(MachineResultModel).all()}
    manifest = test_artifact_dir / "manifest.json"
    payload = json.loads(manifest.read_text())
    payload["config"]["priority_policy"] = "new-policy"
    manifest.write_text(json.dumps(payload))
    execute_ml_ranking(db_session, ws_id, rev_id, artifact_dir=test_artifact_dir)
    rows = db_session.query(MachineResultModel).all()
    assert len(rows) == 6 and original_ids <= {row.id for row in rows}


def test_public_ranking_adapters_use_same_scoped_model(db_session, seeded_workspace, test_artifact_dir, monkeypatch):
    from app.contracts.models import ScreeningRankRequest
    from app.services.screening_rank import rank_screening_groups
    monkeypatch.setenv("EVIDRA_ML_ARTIFACT_DIR", str(test_artifact_dir))
    ws_id, rev_id = seeded_workspace
    canonical = execute_ml_ranking(db_session, ws_id, rev_id)
    legacy = rank_screening_groups(db_session, ws_id, ScreeningRankRequest(revision_id=rev_id))
    assert legacy.status == "available"
    assert [r.group_id for r in legacy.ranked_groups] == [r.group_id for r in canonical.items if r.state == "SCORED"]


@pytest.fixture
def test_artifact_dir(tmp_path: Path) -> Path:
    """Train a reproducible test artifact for fast CI tests."""
    dataset = [
        RecordInput(
            id="rec-pos-1",
            title="Metformin vs placebo in type 2 diabetes trial",
            abstract_text="Randomized controlled clinical trial of metformin in adults with type 2 diabetes.",
            group_id="grp-1",
            label=1,
        ),
        RecordInput(
            id="rec-pos-2",
            title="Clinical efficacy of metformin monotherapy",
            abstract_text="Adult diabetic patients randomized to metformin demonstrated significant HbA1c improvement.",
            group_id="grp-2",
            label=1,
        ),
        RecordInput(
            id="rec-neg-1",
            title="Metformin uptake in rodent liver tissue",
            abstract_text="Sprague Dawley rats administered biguanide. Preclinical animal hepatic tissue study.",
            group_id="grp-3",
            label=0,
        ),
        RecordInput(
            id="rec-neg-2",
            title="In vitro cellular simulation of glucose transport",
            abstract_text="Cell culture assay without human subjects or clinical intervention.",
            group_id="grp-4",
            label=0,
        ),
    ]
    scope = "In adults with type 2 diabetes, how does metformin, compared with placebo or another glucose-lowering intervention, affect HbA1c?"
    train_ranker(
        records=dataset,
        config=TrainConfig(max_features=100, seed=42, val_ratio=0.25, test_ratio=0.25),
        output_dir=tmp_path,
        scope=scope,
    )
    return tmp_path


@pytest.fixture
def seeded_workspace(db_session: Session) -> tuple[str, str]:
    """Seed workspace with criteria, corpus revision, paper groups, and representative records."""
    ws_id = f"ws-ml-{uuid4().hex[:8]}"
    ws = WorkspaceModel(id=ws_id, title="ML Ranking Test Workspace", created_by="test-user")
    db_session.add(ws)
    db_session.flush()

    crit_id = f"crit-{uuid4().hex[:8]}"
    crit = CriteriaVersionModel(
        id=crit_id,
        workspace_id=ws_id,
        sequence=1,
        question="In adults with type 2 diabetes, how does metformin, compared with placebo or another glucose-lowering intervention, affect HbA1c?",
        pico_json="{}",
        criteria_json="{}",
        content_hash="test-crit-hash-123",
    )
    db_session.add(crit)
    db_session.flush()

    rev_id = f"rev-{uuid4().hex[:8]}"
    rev = CorpusRevisionModel(
        id=rev_id,
        workspace_id=ws_id,
        criteria_version_id=crit_id,
        dedup_version="v1.0.0",
        state=CorpusRevisionState.PUBLISHED.value,
        fingerprint="corpus-fp-001",
        group_count=3,
        record_count=3,
    )
    db_session.add(rev)
    db_session.flush()

    # Add 3 records/groups: 1 clinical RCT, 1 preclinical animal, 1 missing abstract
    items_data = [
        (
            "grp-clinical-1",
            "rec-clinical-1",
            "Efficacy of metformin in adult type 2 diabetes RCT",
            "Double-blind randomized controlled trial in 300 diabetic adults.",
        ),
        (
            "grp-animal-2",
            "rec-animal-2",
            "Preclinical rat model of hepatic gluconeogenesis",
            "Animal model testing biguanide in Sprague-Dawley rodents.",
        ),
        (
            "grp-noabs-3",
            "rec-noabs-3",
            "Brief letter to editor on metformin",
            None,  # Missing abstract
        ),
    ]

    for gid, rid, title, abstract in items_data:
        grp = PaperGroupModel(id=gid, workspace_id=ws_id, membership_fingerprint=f"mfp-{gid}")
        db_session.add(grp)

        src = SourceRecordModel(
            id=f"src-{rid}",
            workspace_id=ws_id,
            source="pubmed",
            source_namespace="pubmed",
            external_id=f"ext-{rid}",
        )
        db_session.add(src)
        db_session.flush()

        r_rev = RecordRevisionModel(
            id=rid,
            source_record_id=src.id,
            content_hash=f"hash-{rid}",
            title=title,
            abstract_text=abstract,
        )
        db_session.add(r_rev)
        db_session.flush()

        snap = GroupSnapshotModel(
            corpus_revision_id=rev_id,
            group_id=gid,
            representative_revision_id=r_rev.id,
        )
        db_session.add(snap)

        cm = CorpusMemberModel(
            corpus_revision_id=rev_id,
            source_record_id=src.id,
            record_revision_id=r_rev.id,
        )
        db_session.add(cm)

    db_session.commit()
    return ws_id, rev_id


def test_execute_ml_ranking_success_and_order(
    db_session: Session, seeded_workspace: tuple[str, str], test_artifact_dir: Path
):
    """Test successful ML ranking execution, score distribution, and missing abstract handling."""
    ws_id, rev_id = seeded_workspace
    req = MLRankingRequest(limit=10, offset=0)

    res = execute_ml_ranking(
        db=db_session,
        workspace_id=ws_id,
        revision_id=rev_id,
        request=req,
        artifact_dir=test_artifact_dir,
    )

    assert isinstance(res, MLRankingResponse)
    assert res.workspace_id == ws_id
    assert res.revision_id == rev_id
    assert res.status == "COMPLETED"
    assert res.total_records == 3
    assert res.scored_count == 2
    assert len(res.items) == 3

    # Rank 1 must be the clinical RCT with highest priority score
    rank1 = res.items[0]
    assert rank1.record_id == "rec-clinical-1"
    assert rank1.rank == 1
    assert rank1.state == "SCORED"
    assert rank1.score > 0.4
    assert rank1.priority_label in ("HIGH", "MEDIUM")

    # Missing abstract item must be UNAVAILABLE with MISSING_ABSTRACT
    missing_it = next(it for it in res.items if it.record_id == "rec-noabs-3")
    assert missing_it.state == "UNAVAILABLE"
    assert missing_it.reason == "MISSING_ABSTRACT"
    assert missing_it.score == 0.0
    assert missing_it.priority_label == "UNSCORED"

    # Invariant: ReviewEventModel must NEVER be written by ML ranking
    assert db_session.query(ReviewEventModel).count() == 0

    # Invariant: MachineResultModel must persist 3 cached results
    cached_mrs = db_session.query(MachineResultModel).filter_by(corpus_revision_id=rev_id).all()
    assert len(cached_mrs) == 3

    # Invariant: RunLogModel records successful ML ranking execution
    run_log = db_session.query(RunLogModel).filter_by(stage="ml_ranking", workspace_id=ws_id).first()
    assert run_log is not None
    assert run_log.status == "SUCCESS"


def test_ml_ranking_idempotency_cache(
    db_session: Session, seeded_workspace: tuple[str, str], test_artifact_dir: Path
):
    """Subsequent requests hit MachineResultModel cache and return status CACHED."""
    ws_id, rev_id = seeded_workspace

    # First run computes
    res1 = execute_ml_ranking(
        db=db_session,
        workspace_id=ws_id,
        revision_id=rev_id,
        request=MLRankingRequest(),
        artifact_dir=test_artifact_dir,
    )
    assert res1.status == "COMPLETED"

    # Second run hits cache
    res2 = execute_ml_ranking(
        db=db_session,
        workspace_id=ws_id,
        revision_id=rev_id,
        request=MLRankingRequest(),
        artifact_dir=test_artifact_dir,
    )
    assert res2.status == "CACHED"
    assert res2.total_records == res1.total_records
    assert [it.record_id for it in res2.items] == [it.record_id for it in res1.items]

    # Force recompute bypasses cache
    res3 = execute_ml_ranking(
        db=db_session,
        workspace_id=ws_id,
        revision_id=rev_id,
        request=MLRankingRequest(force_recompute=True),
        artifact_dir=test_artifact_dir,
    )
    assert res3.status == "COMPLETED"


def test_rejection_of_unauthorized_or_unknown_workspace(
    db_session: Session, seeded_workspace: tuple[str, str], test_artifact_dir: Path
):
    """Unknown workspace ID raises 404 HTTPException."""
    _, rev_id = seeded_workspace
    with pytest.raises(HTTPException) as exc_info:
        execute_ml_ranking(
            db=db_session,
            workspace_id="non-existent-workspace",
            revision_id=rev_id,
            artifact_dir=test_artifact_dir,
        )
    assert exc_info.value.status_code == 404


def test_rejection_of_mismatched_corpus_revision(
    db_session: Session, seeded_workspace: tuple[str, str], test_artifact_dir: Path
):
    """Mismatched or unknown revision raises 404 HTTPException."""
    ws_id, _ = seeded_workspace
    with pytest.raises(HTTPException) as exc_info:
        execute_ml_ranking(
            db=db_session,
            workspace_id=ws_id,
            revision_id="unknown-revision-id",
            artifact_dir=test_artifact_dir,
        )
    assert exc_info.value.status_code == 404


def test_empty_corpus_revision_returns_empty_status(
    db_session: Session, seeded_workspace: tuple[str, str], test_artifact_dir: Path
):
    """Revision with 0 groups returns EMPTY status gracefully."""
    ws_id, _ = seeded_workspace
    crit = db_session.query(CriteriaVersionModel).filter_by(workspace_id=ws_id).first()
    assert crit is not None
    empty_rev_id = f"rev-empty-{uuid4().hex[:8]}"
    rev = CorpusRevisionModel(
        id=empty_rev_id,
        workspace_id=ws_id,
        criteria_version_id=crit.id,
        dedup_version="v1.0.0",
        state=CorpusRevisionState.PUBLISHED.value,
        fingerprint="empty-fp",
        group_count=0,
        record_count=0,
    )
    db_session.add(rev)
    db_session.commit()

    res = execute_ml_ranking(
        db=db_session,
        workspace_id=ws_id,
        revision_id=empty_rev_id,
        artifact_dir=test_artifact_dir,
    )
    assert res.status == "EMPTY"
    assert res.total_records == 0
    assert len(res.items) == 0


def test_tampered_or_missing_artifact_graceful_unavailable(
    db_session: Session, seeded_workspace: tuple[str, str], tmp_path: Path
):
    """Corrupt or missing artifact returns UNAVAILABLE without crashing or breaking manual review."""
    ws_id, rev_id = seeded_workspace

    # Empty tmp directory has no manifest
    res = execute_ml_ranking(
        db=db_session,
        workspace_id=ws_id,
        revision_id=rev_id,
        artifact_dir=tmp_path,
    )
    assert res.status == "UNAVAILABLE"
    assert "unavailable" in res.reason.lower() or "missing" in res.reason.lower()
    assert res.scored_count == 0


def test_ml_ranking_api_routes(
    db_session: Session, seeded_workspace: tuple[str, str], client: TestClient
):
    """Test POST and GET /api/v1/workspaces/{workspace_id}/revisions/{revision_id}/ml-ranking."""
    ws_id, rev_id = seeded_workspace

    # POST route computes ranking
    post_res = client.post(
        f"/api/v1/workspaces/{ws_id}/revisions/{rev_id}/ml-ranking",
        json={"limit": 5, "offset": 0},
    )
    assert post_res.status_code == 200
    data = post_res.json()
    assert data["workspace_id"] == ws_id
    assert data["revision_id"] == rev_id
    assert data["total_records"] == 3
    assert len(data["items"]) == 3

    # GET route fetches paginated ranking
    get_res = client.get(
        f"/api/v1/workspaces/{ws_id}/revisions/{rev_id}/ml-ranking?limit=2&offset=0",
    )
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert len(get_data["items"]) == 2
    assert get_data["items"][0]["rank"] == 1
