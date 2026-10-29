"""Offline model training and cryptographic artifact serialization."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import joblib
import sklearn

from app.ml_feature.dataset import (
    compute_records_hash,
    create_leakage_free_split,
)
from app.ml_feature.evaluation import evaluate_scores, operating_threshold
from app.ml_feature.pipeline import build_pipeline, extract_texts_and_labels
from app.ml_feature.types import ArtifactManifest, RecordInput, TrainConfig

DEFAULT_SCOPE = "In adults with type 2 diabetes, how does metformin, compared with placebo or another glucose-lowering intervention, affect HbA1c?"


def compute_file_sha256(path: Path) -> str:
    """Calculate the SHA-256 checksum of a file on disk."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def train_ranker(
    records: list[RecordInput],
    config: TrainConfig,
    output_dir: Path | str,
    scope: str = DEFAULT_SCOPE,
    artifact_version: str = "ml_ranker:v1.0.0",
) -> ArtifactManifest:
    """Train a scikit-learn review prioritization pipeline and save a versioned artifact.

    Strict invariants:
    - Preprocessing and vocabulary fitting are performed exclusively on train split.
    - Model file SHA-256 fingerprint is recorded in manifest.json for tamper protection.
    - Artifact directory contains model.joblib and manifest.json.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # 1. Leakage-free split
    train_recs, val_recs, test_recs = create_leakage_free_split(
        records,
        val_ratio=config.val_ratio,
        test_ratio=config.test_ratio,
        seed=config.seed,
    )

    train_hash = compute_records_hash(train_recs)
    val_hash = compute_records_hash(val_recs)
    test_hash = compute_records_hash(test_recs)

    # 2. Extract texts and labels strictly from training data
    train_texts, train_labels = extract_texts_and_labels(train_recs)

    # 3. Fit pipeline
    pipeline = build_pipeline(config)
    pipeline.fit(train_texts, train_labels)

    vectorizer = pipeline.named_steps["tfidfvectorizer"]
    feature_count = len(vectorizer.vocabulary_)

    # 4. Measure validation metrics if validation set exists
    metrics: dict[str, float] = {}
    if val_recs:
        val_texts, val_labels = extract_texts_and_labels(val_recs)
        preds = pipeline.predict(val_texts)
        probs = pipeline.predict_proba(val_texts)[:, 1] if hasattr(pipeline, "predict_proba") else preds

        correct = sum(p == y for p, y in zip(preds, val_labels, strict=False))
        metrics["val_accuracy"] = round(correct / len(val_labels), 4)

        # Average predicted priority score for positives vs negatives
        pos_scores = [prob for prob, y in zip(probs, val_labels, strict=False) if y == 1]
        neg_scores = [prob for prob, y in zip(probs, val_labels, strict=False) if y == 0]
        if pos_scores:
            metrics["val_mean_pos_score"] = round(sum(pos_scores) / len(pos_scores), 4)
        if neg_scores:
            metrics["val_mean_neg_score"] = round(sum(neg_scores) / len(neg_scores), 4)

    # 5. Serialize model file
    threshold = 0.5
    if val_recs and {r.label for r in val_recs} == {0, 1}:
        threshold = operating_threshold(val_labels, probs)
    # Threshold selection and preprocessing never use final-test labels.
    for name, partition in (("val", val_recs), ("test", test_recs)):
        if not partition:
            continue
        texts, labels = extract_texts_and_labels(partition)
        scores = pipeline.predict_proba(texts)[:, list(pipeline.classes_).index(1)]
        evidence = evaluate_scores(labels, scores, threshold=threshold, ids=[r.id for r in partition])
        metrics.update({f"{name}_{key}": float(value) for key, value in evidence.items()
                        if isinstance(value, (int, float)) and value is not None})
    model_path = out_path / "model.joblib"
    joblib.dump(pipeline, model_path)
    model_sha256 = compute_file_sha256(model_path)

    # 6. Construct and write manifest
    manifest = ArtifactManifest(
        artifact_version=artifact_version,
        model_type="Tfidf_LogisticRegression",
        sklearn_version=sklearn.__version__,
        joblib_version=joblib.__version__,
        created_at=datetime.now(UTC).isoformat(),
        scope=scope,
        feature_count=feature_count,
        train_records_count=len(train_recs),
        train_hash=train_hash,
        val_hash=val_hash,
        test_hash=test_hash,
        model_file_sha256=model_sha256,
        config={**config.model_dump(), "operating_threshold": threshold},
        metrics=metrics,
    )

    manifest_path = out_path / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest.model_dump(), f, indent=2)

    return manifest
