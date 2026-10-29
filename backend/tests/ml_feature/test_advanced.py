"""Leakage, metric and artifact regression tests; no live network or booster dependency."""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pytest
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer

from app.ml_feature.advanced import (
    BoundedSVD,
    SafeTfidf,
    build_challenger,
    feature_rows,
)
from app.ml_feature.dataset import create_leakage_free_split
from app.ml_feature.evaluation import evaluate_scores, operating_threshold
from app.ml_feature.ranker import MLRanker, load_ranker
from app.ml_feature.trainer import compute_file_sha256
from app.ml_feature.types import ArtifactManifest, RankingContext, RecordInput
from app.screening.ml.pipeline import train_ranking_model
from app.screening.ml.types import MLRankingStatus, MLRecordInput


def examples(n=20):
    return [RecordInput(
        id=f"r-{i:03}", group_id=f"g-{i // 2}", label=(i // 2) % 2,
        title="Clinical trial" if (i // 2) % 2 else "Animal experiment",
        abstract_text="Adults receiving metformin versus placebo in a randomized trial" if (i // 2) % 2
        else "Preclinical rats in a laboratory hepatic tissue experiment",
    ) for i in range(n)]


def test_split_is_order_invariant_and_groups_do_not_cross():
    records = examples(40)
    first = create_leakage_free_split(records)
    second = create_leakage_free_split(list(reversed(records)))
    assert [[r.id for r in s] for s in first] == [[r.id for r in s] for s in second]
    groups = [{r.group_id for r in s} for s in first]
    assert not (groups[0] & groups[1] or groups[0] & groups[2] or groups[1] & groups[2])


def test_rejects_invalid_split_and_duplicate_ids():
    with pytest.raises(ValueError, match="sum"):
        create_leakage_free_split(examples(), val_ratio=.6, test_ratio=.5)
    with pytest.raises(ValueError, match="Duplicate"):
        create_leakage_free_split(examples() + examples())


def test_column_features_train_only_and_empty_abstract_branch():
    records = examples()
    for r in records:
        r.abstract_text = ""
    model = build_challenger("logistic")
    model.fit(feature_rows(records), [r.label for r in records])
    unseen = RecordInput(id="unseen", title="Secretcanaryterm clinical trial", abstract_text="Unseen abstract vocabulary")
    scores = model.predict_proba(feature_rows([unseen]))
    assert scores.shape == (1, 2) and np.isfinite(scores).all()
    vocab = model.named_steps["features"].named_transformers_["title"].vectorizer_.vocabulary_
    assert "secretcanaryterm" not in vocab
    assert model.named_steps["features"].named_transformers_["abstract"].empty_
    assert "label" not in model.named_steps["features"].get_feature_names_out().tolist()


def test_empty_vectorizer_and_svd_bounds():
    vectorizer = SafeTfidf().fit(["", ""])
    assert vectorizer.transform(["unseen"]).shape == (1, 1)
    matrix = TfidfVectorizer().fit_transform(["adult clinical trial", "rat tissue experiment", "clinical placebo trial"])
    reducer = BoundedSVD(n_components=100).fit(matrix)
    assert reducer.transform(matrix).shape == (3, 2)


def test_metrics_known_confusion_and_discrete_wss():
    m = evaluate_scores([1, 0, 1, 0], [.9, .8, .7, .1], threshold=.75, ids=["a", "b", "c", "d"])
    assert m["confusion"] == {"tp": 1, "fp": 1, "tn": 1, "fn": 1}
    assert m["accuracy"] == m["precision"] == m["recall"] == m["f1"] == .5
    assert m["screened_at_95"] == 3
    assert m["wss_at_95"] == pytest.approx(.2)
    assert m["actual_recall_at_95"] == 1.0


def test_no_positive_metrics_are_undefined_and_ties_use_ids():
    m = evaluate_scores([0, 0], [.2, .1])
    assert m["recall"] is None and m["wss_at_95"] is None
    assert m["average_precision"] is None
    tied = evaluate_scores([1, 0], [.5, .5], ids=["z", "a"])
    assert tied["screened_at_95"] == 2
    with pytest.raises(ValueError, match="positive"):
        operating_threshold([0, 0], [.2, .1])


@pytest.mark.parametrize("labels,scores", [([None, 1], [.2, .8]), ([0, 1], [float("nan"), .8]),
                                         ([0, 1], [1.1, .8]), ([0], [.1, .2])])
def test_invalid_metric_inputs_rejected(labels, scores):
    with pytest.raises(ValueError):
        evaluate_scores(labels, scores)


def test_development_threshold_meets_requested_recall():
    labels, scores = [1, 1, 0, 0], [.8, .3, .5, .1]
    threshold = operating_threshold(labels, scores)
    assert threshold == .3
    assert evaluate_scores(labels, scores, threshold=threshold)["recall"] == 1.0


@pytest.mark.parametrize("bad_label", [None, "MAYBE", "UNSCREENED", "unknown"])
def test_old_training_port_does_not_coerce_unknown_labels_to_negative(bad_label):
    records = [MLRecordInput(id=str(i), title="Clinical example", abstract="Clinical abstract", label=label)
               for i, label in enumerate(["INCLUDE", "EXCLUDE", "INCLUDE", bad_label])]
    model, state, _, _ = train_ranking_model(records)
    assert model is None and state == MLRankingStatus.UNAVAILABLE_INVALID_LABEL


def test_heterogeneous_bundle_roundtrip_and_scope(tmp_path: Path):
    records = examples()
    model = build_challenger("logistic", character=True)
    model.fit(feature_rows(records), [r.label for r in records])
    model_path = tmp_path / "model.joblib"
    joblib.dump(model, model_path)
    manifest = ArtifactManifest(
        artifact_version="test-advanced", model_type="logistic", sklearn_version=sklearn.__version__,
        joblib_version=joblib.__version__, created_at="2026-10-29", scope="trusted question",
        feature_count=5, train_records_count=len(records), train_hash="a", val_hash="b", test_hash="c",
        model_file_sha256=compute_file_sha256(model_path), config={"input_schema": "heterogeneous-v1"})
    path = tmp_path / "manifest.json"
    path.write_text(manifest.model_dump_json())
    ranker = load_ranker(tmp_path, expected_scope="trusted question")
    result = ranker.rank_records(records, RankingContext(review_question="trusted question"))
    assert result.scored_count == len(records)
    assert records[0].label == 0  # Inference does not mutate labels.
    assert ranker.rank_records(records, RankingContext(review_question="other")).scored_count == 0
    payload = json.loads(path.read_text())
    payload["config"]["input_schema"] = "unknown"
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="schema"):
        load_ranker(tmp_path)


class AlmostTiedModel:
    classes_ = np.asarray([0, 1])

    def __init__(self):
        self.calls = 0

    def predict_proba(self, texts):
        self.calls += 1
        return np.asarray([[.49996, .50004] if "higher" in text else [.49997, .50003] for text in texts])


def test_batching_keeps_precision_before_sort():
    from app.ml_feature.types import ArtifactManifest
    manifest = ArtifactManifest(
        artifact_version="t", sklearn_version=sklearn.__version__, joblib_version=joblib.__version__,
        created_at="2026-10-29", scope="q", feature_count=1, train_records_count=4,
        train_hash="a", val_hash="b", test_hash="c", model_file_sha256="d", config={})
    model = AlmostTiedModel()
    ranker = MLRanker(model, manifest)
    records = [RecordInput(id="a", title="lower", abstract_text="Long enough abstract"),
               RecordInput(id="z", title="higher", abstract_text="Long enough abstract")]
    result = ranker.rank_records(records, RankingContext(review_question="q"))
    assert result.items[0].record_id == "z"
    assert model.calls == 1


def test_active_learning_reveals_labels_sequentially_and_obeys_budget():
    from app.ml_feature.active_learning import simulate_review
    records = examples(20)
    initial = [r.id for r in records[:4]]
    result = simulate_review(records, initial, budget=10, batch_size=2)
    assert len(result["queried_ids"]) == 10
    assert len(set(result["queried_ids"])) == 10
    for fit_ids in result["fit_label_ids"]:
        assert fit_ids == result["queried_ids"][:len(fit_ids)]
        assert len(fit_ids) < 10
    assert result["history"][-1]["reviewed"] == 10


def test_early_stop_eval_set_uses_train_fitted_transformations():
    from app.ml_feature.advanced import fit_with_early_stopping

    class RecordingBooster:
        def set_params(self, **params):
            return self

        def fit(self, X, y, *, eval_set, verbose):
            self.train_shape = X.shape
            self.validation_shape = eval_set[0][0].shape

    train = examples(8)
    validation = [RecordInput(id="holdout", group_id="holdout", label=1,
                              title="Secretvalidationtoken", abstract_text="Only held out words")]
    pipeline = build_challenger("logistic")
    booster = RecordingBooster()
    pipeline.steps[-1] = ("classifier", booster)
    fit_with_early_stopping(pipeline, train, validation, family="xgboost")
    assert booster.train_shape[1] == booster.validation_shape[1]
    vocabulary = pipeline.named_steps["features"].named_transformers_["title"].vectorizer_.vocabulary_
    assert "secretvalidationtoken" not in vocabulary
    with pytest.raises(ValueError, match="disjoint"):
        fit_with_early_stopping(pipeline, train, train[:1], family="xgboost")
