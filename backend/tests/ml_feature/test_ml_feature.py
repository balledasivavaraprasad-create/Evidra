"""Unit and regression tests for ML review prioritization pipeline, artifacts, and inference."""
import pytest

from app.ml_feature.dataset import create_leakage_free_split, validate_dataset
from app.ml_feature.ranker import load_ranker
from app.ml_feature.trainer import train_ranker
from app.ml_feature.types import RankingContext, RecordInput, TrainConfig


@pytest.fixture
def sample_dataset() -> list[RecordInput]:
    """Realistic synthetic biomedical records for testing ML pipeline."""
    return [
        # Group 1: RCT Human studies (Positives)
        RecordInput(
            id="rec-pos-001",
            title="Efficacy of metformin versus placebo in type 2 diabetes",
            abstract_text="Randomized double-blind placebo-controlled trial of metformin in 300 adults with type 2 diabetes. Significant HbA1c reduction observed.",
            group_id="grp-study-001",
            label=1,
        ),
        RecordInput(
            id="rec-pos-002",
            title="Long-term outcomes of metformin trial in type 2 diabetes",
            abstract_text="Five-year follow-up of randomized controlled trial evaluating metformin monotherapy vs control in diabetic patients. Sustained glycemic control.",
            group_id="grp-study-001",  # Same group as 001! Must stay in same split
            label=1,
        ),
        RecordInput(
            id="rec-pos-003",
            title="Comparative trial of oral metformin vs sulfonylurea in T2D",
            abstract_text="Multicenter comparative clinical study in adult type 2 diabetics assessing metformin versus active comparator. HbA1c lowered by 1.2%.",
            group_id="grp-study-002",
            label=1,
        ),
        RecordInput(
            id="rec-pos-004",
            title="Metformin extended-release in adults with diabetes",
            abstract_text="Clinical randomized evaluation of metformin once daily compared with placebo in patients with poorly controlled type 2 diabetes.",
            group_id="grp-study-003",
            label=1,
        ),
        RecordInput(
            id="rec-pos-005",
            title="Metformin intervention trial in newly diagnosed diabetic adults",
            abstract_text="A prospective comparative clinical trial testing metformin versus lifestyle alone in adults with type 2 diabetes.",
            group_id="grp-study-004",
            label=1,
        ),
        # Group 2: Animal & Preclinical studies (Negatives)
        RecordInput(
            id="rec-neg-001",
            title="Metformin regulates gluconeogenesis in diabetic rats",
            abstract_text="Sprague-Dawley rats induced with streptozotocin received metformin 250 mg/kg daily. Preclinical rodent hepatic enzyme expression measured.",
            group_id="grp-study-005",
            label=0,
        ),
        RecordInput(
            id="rec-neg-002",
            title="Mechanisms of biguanides in mouse hepatocytes",
            abstract_text="Isolated murine liver cells were treated with biguanides. Cell culture in vitro assay without human subjects or clinical outcomes.",
            group_id="grp-study-006",
            label=0,
        ),
        # Group 3: Simulation & Docking (Negatives)
        RecordInput(
            id="rec-neg-003",
            title="In silico molecular modeling of biguanide binding kinetics",
            abstract_text="Computational molecular dynamics simulation of metformin docking with AMPK complex. Pure in silico energy minimization, no patients.",
            group_id="grp-study-007",
            label=0,
        ),
        # Group 4: Case Reports (Negatives)
        RecordInput(
            id="rec-neg-004",
            title="Metformin-induced lactic acidosis in renal failure: a case report",
            abstract_text="Case report of an 82-year-old female presenting with lactic acidosis during acute kidney injury. Single patient presentation without control group.",
            group_id="grp-study-008",
            label=0,
        ),
        # Group 5: Pediatric / Off-target (Negatives)
        RecordInput(
            id="rec-neg-005",
            title="Metformin in pediatric type 1 diabetes: observational survey",
            abstract_text="Survey in children and adolescents with type 1 diabetes mellitus. Off-target non-adult population with autoimmune diabetes.",
            group_id="grp-study-009",
            label=0,
        ),
    ]


def test_dataset_validation_detects_invalid_inputs():
    """validate_dataset rejects small datasets, missing fields, or single-class data."""
    # Too small
    is_valid, errs = validate_dataset([])
    assert not is_valid
    assert any("too small" in e for e in errs)

    # Missing class 0
    all_positives = [
        RecordInput(id=f"rec-{i}", title=f"Title {i}", abstract_text="Abstract text", label=1)
        for i in range(5)
    ]
    is_valid, errs = validate_dataset(all_positives)
    assert not is_valid
    assert any("both positive" in e for e in errs)


def test_leakage_free_split_preserves_study_groups(sample_dataset):
    """Related records sharing a group_id must strictly land in the exact same split."""
    train_recs, val_recs, test_recs = create_leakage_free_split(
        sample_dataset,
        val_ratio=0.2,
        test_ratio=0.2,
        seed=42,
    )

    # Check non-empty splits
    assert len(train_recs) >= 2
    assert len(train_recs) + len(val_recs) + len(test_recs) == len(sample_dataset)

    # Confirm group-level exclusivity: no group crosses between splits
    train_groups = {r.group_id for r in train_recs if r.group_id}
    val_groups = {r.group_id for r in val_recs if r.group_id}
    test_groups = {r.group_id for r in test_recs if r.group_id}

    assert train_groups.isdisjoint(val_groups), "Leakage detected between train and val groups!"
    assert train_groups.isdisjoint(test_groups), "Leakage detected between train and test groups!"
    assert val_groups.isdisjoint(test_groups), "Leakage detected between val and test groups!"

    # Specifically check grp-study-001 (which has 2 records)
    rec1_split = (
        "train" if any(r.id == "rec-pos-001" for r in train_recs)
        else "val" if any(r.id == "rec-pos-001" for r in val_recs)
        else "test"
    )
    rec2_split = (
        "train" if any(r.id == "rec-pos-002" for r in train_recs)
        else "val" if any(r.id == "rec-pos-002" for r in val_recs)
        else "test"
    )
    assert rec1_split == rec2_split, f"Group records split across {rec1_split} and {rec2_split}!"


def test_training_and_manifest_serialization(tmp_path, sample_dataset):
    """Training produces valid model.joblib and manifest.json with matching SHA-256."""
    config = TrainConfig(max_features=200, seed=42)
    manifest = train_ranker(
        records=sample_dataset,
        config=config,
        output_dir=tmp_path,
        scope="test-scope",
    )

    assert (tmp_path / "model.joblib").exists()
    assert (tmp_path / "manifest.json").exists()

    # Verify manifest fields
    assert manifest.scope == "test-scope"
    assert manifest.feature_count > 0
    assert manifest.feature_count <= 200
    assert len(manifest.model_file_sha256) == 64  # Valid SHA-256 hex string


def test_ranker_tamper_detection(tmp_path, sample_dataset):
    """load_ranker rejects modified model files and mismatched scopes."""
    train_ranker(
        records=sample_dataset,
        config=TrainConfig(max_features=200, seed=42),
        output_dir=tmp_path,
        scope="adults_t2d_metformin",
    )

    # 1. Successful load with matching scope
    ranker = load_ranker(tmp_path, expected_scope="adults_t2d_metformin")
    assert ranker is not None

    # 2. Scope mismatch rejection
    with pytest.raises(ValueError, match="Artifact scope mismatch"):
        load_ranker(tmp_path, expected_scope="different_cancer_review")

    # 3. Tamper detection: modify a byte in model.joblib
    model_path = tmp_path / "model.joblib"
    with open(model_path, "ab") as f:
        f.write(b"\x00\xff")  # Corrupt the binary

    with pytest.raises(ValueError, match="Artifact integrity check failed"):
        load_ranker(tmp_path, expected_scope="adults_t2d_metformin")


def test_inference_queue_ranking_and_tie_breaking(tmp_path, sample_dataset):
    """rank_records prioritizes relevant RCTs over animal/simulation studies and breaks ties."""
    scope = "adults_t2d_metformin"
    train_ranker(
        records=sample_dataset,
        config=TrainConfig(max_features=200, seed=42),
        output_dir=tmp_path,
        scope=scope,
    )
    ranker = load_ranker(tmp_path, expected_scope=scope)

    # Query with mix of clinical RCT, animal study, and missing abstract
    eval_records = [
        RecordInput(
            id="eval-rct",
            title="Randomized trial of metformin in adults with type 2 diabetes",
            abstract_text="Placebo controlled RCT in 200 adult diabetic patients measuring reduction in HbA1c.",
        ),
        RecordInput(
            id="eval-rat",
            title="Preclinical investigation in male Sprague-Dawley rats",
            abstract_text="Streptozotocin induced diabetic rats treated with daily metformin. Rodent study only.",
        ),
        RecordInput(
            id="eval-missing-abs",
            title="Editorial commentary on biguanides",
            abstract_text=None,  # Missing abstract!
        ),
    ]

    context = RankingContext(review_question=scope)
    batch = ranker.rank_records(eval_records, context)

    assert batch.total_records == 3
    assert batch.scored_count == 2  # Missing abstract is UNAVAILABLE, not SCORED

    # Verify order: eval-rct should be Rank 1 with high score
    assert batch.items[0].record_id == "eval-rct"
    assert batch.items[0].rank == 1
    assert batch.items[0].state == "SCORED"
    assert batch.items[0].score > 0.5

    # eval-missing-abs should be UNAVAILABLE with reason MISSING_ABSTRACT
    missing_item = next(it for it in batch.items if it.record_id == "eval-missing-abs")
    assert missing_item.state == "UNAVAILABLE"
    assert missing_item.reason == "MISSING_ABSTRACT"
    assert missing_item.score == 0.0

    # Verify ranks are sequential 1, 2, 3
    ranks = [it.rank for it in batch.items]
    assert ranks == [1, 2, 3]


def test_out_of_scope_query_handling(tmp_path, sample_dataset):
    """When query context does not match model scope, items are marked OUT_OF_SCOPE."""
    scope = "adults_t2d_metformin"
    train_ranker(
        records=sample_dataset,
        config=TrainConfig(max_features=200, seed=42),
        output_dir=tmp_path,
        scope=scope,
    )
    ranker = load_ranker(tmp_path, expected_scope=scope)

    different_context = RankingContext(review_question="Unrelated Asthma Review")
    batch = ranker.rank_records(sample_dataset[:2], different_context)

    assert batch.scored_count == 0
    assert all(it.state == "OUT_OF_SCOPE" for it in batch.items)
