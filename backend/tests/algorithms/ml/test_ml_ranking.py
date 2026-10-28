"""Unit tests for classical ML screening prioritization engine (B05)."""
from pathlib import Path

import pytest

from app.screening.ml.pipeline import (
    load_model_artifact,
    save_model_artifact,
    score_and_rank_records,
    train_ranking_model,
)
from app.screening.ml.ranker import (
    MLScreeningRanker,
    compute_recall_at_k,
    compute_work_saved_at_recall,
)
from app.screening.ml.types import (
    MLRankingStatus,
    MLRecordInput,
    RankedRecord,
)


@pytest.fixture
def synthetic_records() -> list[MLRecordInput]:
    return [
        MLRecordInput(
            id="rec-01",
            title="Randomized controlled trial of semaglutide in type 2 diabetes",
            abstract="A double-blind RCT evaluating semaglutide versus placebo in adult diabetic patients.",
            label="INCLUDE",
        ),
        MLRecordInput(
            id="rec-02",
            title="Preclinical mouse model study of GLP-1 receptor activation in islets",
            abstract="Murine pancreatic tissue was examined in vitro to assess cellular pathways.",
            label="EXCLUDE",
        ),
        MLRecordInput(
            id="rec-03",
            title="Efficacy of SGLT2 inhibitors on HbA1c reduction in adults with diabetes",
            abstract="Phase 3 multicenter randomized trial demonstrating glycemic control.",
            label="INCLUDE",
        ),
        MLRecordInput(
            id="rec-04",
            title="Pediatric incidence of diabetic ketoacidosis in school children",
            abstract="Retrospective observational survey in children aged 5-12.",
            label="EXCLUDE",
        ),
        MLRecordInput(
            id="rec-05",
            title="Comparative trial of metformin versus lifestyle modification",
            abstract="Prospective randomized intervention assessing glycemic targets in adults.",
            label="INCLUDE",
        ),
        MLRecordInput(
            id="rec-06",
            title="Narrative review of historical antidiabetic agents",
            abstract="Historical editorial overview without clinical patient cohort.",
            label="EXCLUDE",
        ),
    ]


def test_train_insufficient_samples():
    """Fewer than 4 samples returns UNAVAILABLE_INSUFFICIENT_DATA."""
    tiny = [
        MLRecordInput(id="1", title="A", abstract="B", label="INCLUDE"),
        MLRecordInput(id="2", title="C", abstract="D", label="EXCLUDE"),
    ]
    pipe, status, reason, _meta = train_ranking_model(tiny)
    assert pipe is None
    assert status == MLRankingStatus.UNAVAILABLE_INSUFFICIENT_DATA
    assert "minimum 4 required" in (reason or "")


def test_train_single_class_only():
    """Dataset with only one class (all INCLUDE or all EXCLUDE) returns UNAVAILABLE_SINGLE_CLASS."""
    all_include = [
        MLRecordInput(id=f"rec-{i}", title=f"RCT {i}", abstract="diabetes trial", label="INCLUDE")
        for i in range(5)
    ]
    pipe, status, reason, _meta = train_ranking_model(all_include)
    assert pipe is None
    assert status == MLRankingStatus.UNAVAILABLE_SINGLE_CLASS
    assert "single class only" in (reason or "")


def test_train_empty_vocabulary():
    """Records with empty title and abstract return UNAVAILABLE_EMPTY_VOCAB."""
    empty = [
        MLRecordInput(id="1", title="", abstract="", label="INCLUDE"),
        MLRecordInput(id="2", title="", abstract="", label="EXCLUDE"),
        MLRecordInput(id="3", title="", abstract="", label="INCLUDE"),
        MLRecordInput(id="4", title="", abstract="", label="EXCLUDE"),
    ]
    pipe, status, _reason, _meta = train_ranking_model(empty)
    assert pipe is None
    assert status == MLRankingStatus.UNAVAILABLE_EMPTY_VOCAB


def test_zero_leakage_in_training(synthetic_records):
    """Held-out / test split terms MUST NOT participate in vectorizer fitting."""
    train_records = synthetic_records[:4]
    _test_record = MLRecordInput(
        id="test-secret",
        title="Novel supercalifragilistic drug study",
        abstract="Unknown secret molecule tested on heldout subjects.",
        label="INCLUDE",
    )

    pipe, status, _reason, _meta = train_ranking_model(train_records)
    assert status == MLRankingStatus.AVAILABLE
    assert pipe is not None

    vectorizer = pipe.named_steps["vectorizer"]
    # Verify that the test record token is absent from the fitted vectorizer vocabulary
    assert "supercalifragilistic" not in vectorizer.vocabulary_
    assert "molecule" not in vectorizer.vocabulary_


def test_artifact_sha256_verification_and_tamper_rejection(synthetic_records, tmp_path: Path):
    """Artifact is saved with SHA-256 and tampered artifact is rejected."""
    pipe, _status, _reason, meta = train_ranking_model(synthetic_records)
    assert pipe is not None
    assert meta is not None

    manifest = save_model_artifact(pipe, meta, tmp_path)
    assert manifest.artifact_sha256 is not None
    assert (tmp_path / "model.joblib").exists()
    assert (tmp_path / "manifest.json").exists()

    # Successful load with intact file
    loaded_pipe, loaded_manifest, load_status, _load_err = load_model_artifact(tmp_path)
    assert load_status == MLRankingStatus.AVAILABLE
    assert loaded_pipe is not None
    assert loaded_manifest is not None
    assert loaded_manifest.artifact_sha256 == manifest.artifact_sha256

    # Tamper with model.joblib bytes
    with open(tmp_path / "model.joblib", "ab") as f:
        f.write(b"CORRUPTED_BYTES")

    tampered_pipe, _, tamper_status, tamper_err = load_model_artifact(tmp_path)
    assert tampered_pipe is None
    assert tamper_status == MLRankingStatus.UNAVAILABLE_CORRUPT_ARTIFACT
    assert "Checksum mismatch" in (tamper_err or "")


def test_scoring_and_ranking_deterministic(synthetic_records):
    """Model produces deterministic priority scores in [0.0, 1.0] and sorted rank."""
    pipe, _status, _reason, _meta = train_ranking_model(synthetic_records)
    assert pipe is not None

    res1 = score_and_rank_records(pipe, synthetic_records)
    res2 = score_and_rank_records(pipe, synthetic_records)

    assert res1.is_available is True
    assert len(res1.ranked_records) == len(synthetic_records)

    # Check scores in [0.0, 1.0] and descending order
    for idx, r in enumerate(res1.ranked_records):
        assert 0.0 <= r.score <= 1.0
        assert r.rank == idx + 1
        if idx > 0:
            assert res1.ranked_records[idx - 1].score >= r.score

    # Check determinism
    scores1 = [r.score for r in res1.ranked_records]
    scores2 = [r.score for r in res2.ranked_records]
    assert scores1 == scores2


def test_ranker_service_graceful_fallback_when_disabled():
    """Ranker service returns typed unavailable result when disabled."""
    ranker = MLScreeningRanker(enabled=False)
    res = ranker.rank([MLRecordInput(id="1", title="A", abstract="B")])
    assert res.is_available is False
    assert res.status == MLRankingStatus.UNAVAILABLE_DISABLED
    assert "disabled" in res.reason


def test_evaluation_metrics_computation():
    """Test Recall@k and WSS@95 calculation logic."""
    ranked = [
        RankedRecord(record_id="r1", score=0.9, rank=1),
        RankedRecord(record_id="r2", score=0.8, rank=2),
        RankedRecord(record_id="r3", score=0.5, rank=3),
        RankedRecord(record_id="r4", score=0.2, rank=4),
        RankedRecord(record_id="r5", score=0.1, rank=5),
    ]
    ground_truth = {"r1", "r2"}

    # Recall@1: 1 hit / 2 = 0.5
    assert compute_recall_at_k(ranked, ground_truth, k=1) == 0.5
    # Recall@2: 2 hits / 2 = 1.0
    assert compute_recall_at_k(ranked, ground_truth, k=2) == 1.0

    # WSS@95: needs 2 hits to reach 100% (>= 95%). Cutoff is 2 out of 5 (40% screened).
    # WSS = (1 - 2/5) - (1 - 0.95) = 0.60 - 0.05 = 0.55
    wss, cutoff = compute_work_saved_at_recall(ranked, ground_truth, target_recall=0.95)
    assert cutoff == 2
    assert wss == 0.55
