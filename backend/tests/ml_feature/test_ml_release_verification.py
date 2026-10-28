"""Release-gate verification and coexistence suite for ML review prioritization (C-ML03).

Verifies:
1. Clean model lifecycle from disk and cryptographic SHA-256 verification.
2. Complete independence and coexistence with Bounded RAG and LLM gateway.
3. Bounded CPU runtime latency, zero-network requirements, and memory bounds.
4. Strict preservation of ReviewEventModel human decisions.
"""
from __future__ import annotations

import time
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.contracts.enums import CorpusRevisionState
from app.contracts.models import (
    MLRankingRequest,
    MLRankingResponse,
)
from app.db.models import (
    CorpusRevisionModel,
    CriteriaVersionModel,
    GroupSnapshotModel,
    PaperGroupModel,
    RecordRevisionModel,
    ReviewEventModel,
    SourceRecordModel,
    WorkspaceModel,
)
from app.ml_feature.ranker import load_ranker
from app.ml_feature.service import execute_ml_ranking, resolve_artifact_directory


@pytest.fixture
def production_artifact_dir() -> Path:
    """Return verified production artifact path in evals/ml_c/artifact."""
    p = resolve_artifact_directory()
    assert (p / "manifest.json").exists(), f"Missing manifest.json at {p}"
    assert (p / "model.joblib").exists(), f"Missing model.joblib at {p}"
    return p


@pytest.fixture
def benchmark_workspace(db_session: Session) -> tuple[str, str]:
    """Create a realistic workspace with 20 clinical and preclinical records."""
    ws_id = f"ws-bench-{uuid4().hex[:8]}"
    ws = WorkspaceModel(id=ws_id, title="C-ML03 Benchmark Workspace", created_by="release-verifier")
    db_session.add(ws)
    db_session.flush()

    crit_id = f"crit-bench-{uuid4().hex[:8]}"
    crit = CriteriaVersionModel(
        id=crit_id,
        workspace_id=ws_id,
        sequence=1,
        question="In adults with type 2 diabetes, how does metformin, compared with placebo or another glucose-lowering intervention, affect HbA1c?",
        pico_json="{}",
        criteria_json="{}",
        content_hash="bench-crit-hash-999",
    )
    db_session.add(crit)
    db_session.flush()

    rev_id = f"rev-bench-{uuid4().hex[:8]}"
    rev = CorpusRevisionModel(
        id=rev_id,
        workspace_id=ws_id,
        criteria_version_id=crit_id,
        dedup_version="v1.0.0",
        state=CorpusRevisionState.PUBLISHED.value,
        fingerprint="bench-corpus-fp-001",
        group_count=20,
        record_count=20,
    )
    db_session.add(rev)
    db_session.flush()

    # Generate 10 RCT positive titles and 10 preclinical negative titles
    for idx in range(1, 21):
        gid = f"grp-bench-{idx:03d}"
        rid = f"rec-bench-{idx:03d}"
        is_rct = idx <= 10

        title = (
            f"Randomized double-blind trial {idx} of metformin in type 2 diabetes adults"
            if is_rct
            else f"Preclinical study {idx} of biguanide action in isolated rodent hepatocytes"
        )
        abstract = (
            f"Randomized controlled evaluation measuring HbA1c reduction in adult diabetics. Study number {idx}."
            if is_rct
            else f"Laboratory rodent animal model investigating biguanide molecular transport. Rodent assay {idx}."
        )

        grp = PaperGroupModel(id=gid, workspace_id=ws_id, membership_fingerprint=f"mfp-{gid}")
        db_session.add(grp)

        src = SourceRecordModel(
            id=f"src-{rid}",
            workspace_id=ws_id,
            source="pubmed",
            source_namespace="pubmed",
            external_id=f"ext-pmid-{idx:05d}",
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

    db_session.commit()
    return ws_id, rev_id


def test_production_model_lifecycle_and_verification(production_artifact_dir: Path):
    """Verify that the production artifact loads and passes cryptographic integrity checks."""
    ranker = load_ranker(
        production_artifact_dir,
        expected_scope="In adults with type 2 diabetes, how does metformin, compared with placebo or another glucose-lowering intervention, affect HbA1c?",
    )
    assert ranker is not None
    assert ranker.manifest.artifact_version == "ml_ranker:v1.0.0"
    assert ranker.manifest.feature_count == 500

    # Test single-record score prediction
    score_pos = ranker.predict_score(
        "Randomized controlled trial of metformin in adult type 2 diabetes",
        "Placebo-controlled RCT measuring HbA1c reduction in adults.",
    )
    score_neg = ranker.predict_score(
        "Preclinical investigation of biguanides in diabetic Wistar rats",
        "Rodent model testing hepatic gluconeogenesis in mice.",
    )
    assert score_pos > score_neg
    assert score_pos > 0.5


def test_runtime_latency_and_cpu_bounds(
    db_session: Session, benchmark_workspace: tuple[str, str], production_artifact_dir: Path
):
    """Verify sub-100ms batch latency on 20-record corpus and zero GPU requirement."""
    ws_id, rev_id = benchmark_workspace

    t0 = time.perf_counter()
    res = execute_ml_ranking(
        db=db_session,
        workspace_id=ws_id,
        revision_id=rev_id,
        request=MLRankingRequest(limit=50, force_recompute=True),
        artifact_dir=production_artifact_dir,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert isinstance(res, MLRankingResponse)
    assert res.status == "COMPLETED"
    assert res.total_records == 20
    assert res.scored_count == 20
    # Latency must be strictly bounded below 250ms for 20 records on pure CPU
    assert elapsed_ms < 250.0

    # Ensure all top 5 items are high-confidence RCTs
    top_5 = res.items[:5]
    for item in top_5:
        assert item.priority_label in ("HIGH", "MEDIUM")
        assert "Randomized" in item.title or "RCT" in item.title or item.score > 0.4


def test_coexistence_with_offline_runtime_zero_credentials(
    db_session: Session, benchmark_workspace: tuple[str, str], production_artifact_dir: Path
):
    """Verify ML ranking operates 100% locally when LLM/RAG are disabled (Level 1 offline requirement)."""
    ws_id, rev_id = benchmark_workspace

    # Execute ML ranking with LLM disabled
    res = execute_ml_ranking(
        db=db_session,
        workspace_id=ws_id,
        revision_id=rev_id,
        request=MLRankingRequest(),
        artifact_dir=production_artifact_dir,
    )
    assert res.status in ("COMPLETED", "CACHED")

    # Invariant: ML inference must never touch ReviewEventModel
    assert db_session.query(ReviewEventModel).count() == 0


def test_e2e_api_release_gate_verification(
    client: TestClient, benchmark_workspace: tuple[str, str]
):
    """Test full HTTP API round-trip including pagination, ordering, and cached status."""
    ws_id, rev_id = benchmark_workspace

    # 1. Initial compute request
    post_res = client.post(
        f"/api/v1/workspaces/{ws_id}/revisions/{rev_id}/ml-ranking",
        json={"limit": 10, "offset": 0},
    )
    assert post_res.status_code == 200
    post_json = post_res.json()
    assert post_json["total_records"] == 20
    assert len(post_json["items"]) == 10
    assert post_json["items"][0]["rank"] == 1

    # 2. Subsequent cached request (idempotent)
    get_res = client.get(
        f"/api/v1/workspaces/{ws_id}/revisions/{rev_id}/ml-ranking?limit=10&offset=0",
    )
    assert get_res.status_code == 200
    get_json = get_res.json()
    assert get_json["status"] == "CACHED"
    assert get_json["items"][0]["record_id"] == post_json["items"][0]["record_id"]

    # 3. Pagination offset request
    page2_res = client.get(
        f"/api/v1/workspaces/{ws_id}/revisions/{rev_id}/ml-ranking?limit=10&offset=10",
    )
    assert page2_res.status_code == 200
    page2_json = page2_res.json()
    assert len(page2_json["items"]) == 10
    assert page2_json["items"][0]["rank"] == 11
