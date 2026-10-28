"""Leakage-safe training and serialization pipeline for classical ML ranking (B05)."""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
from typing import Any

import joblib
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from app.screening.ml.types import (
    MLModelManifest,
    MLRankingResult,
    MLRankingStatus,
    MLRecordInput,
    RankedRecord,
)

DEFAULT_FEATURE_CONFIG = {
    "max_features": 500,
    "ngram_range": (1, 2),
    "sublinear_tf": True,
    "stop_words": "english",
    "class_weight": "balanced",
    "c_param": 1.0,
    "seed": 42,
}


def compute_bytes_sha256(data: bytes) -> str:
    """Calculate SHA-256 hash of bytes."""
    return hashlib.sha256(data).hexdigest()


def compute_file_sha256(path: Path) -> str:
    """Calculate SHA-256 hash of a file on disk."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def extract_record_text(record: MLRecordInput) -> str:
    """Combine title and abstract deterministically."""
    title = (record.title or "").strip()
    abstract = (record.abstract or "").strip()
    return f"{title} {abstract}".strip()


def train_ranking_model(
    train_records: list[MLRecordInput],
    feature_config: dict[str, Any] | None = None,
    model_version: str = "classical_ranker:v1.0.0",
) -> tuple[Pipeline | None, MLRankingStatus, str | None, dict[str, Any] | None]:
    """Train a TF-IDF + LogisticRegression pipeline strictly on training data.
    
    Guarantees:
    - Zero data leakage: fits solely on train_records.
    - Gracefully handles tiny datasets, empty vocabulary, and single-class scenarios.
    """
    config = dict(DEFAULT_FEATURE_CONFIG)
    if feature_config:
        config.update(feature_config)

    if not train_records or len(train_records) < 4:
        return (
            None,
            MLRankingStatus.UNAVAILABLE_INSUFFICIENT_DATA,
            f"Insufficient training samples: provided {len(train_records)} (minimum 4 required).",
            None,
        )

    texts: list[str] = []
    labels: list[int] = []
    pos_count = 0
    neg_count = 0

    for r in train_records:
        txt = extract_record_text(r)
        texts.append(txt)
        # 1 for INCLUDE, 0 for EXCLUDE / other
        lbl_str = (r.label or "EXCLUDE").upper()
        if lbl_str == "INCLUDE":
            labels.append(1)
            pos_count += 1
        else:
            labels.append(0)
            neg_count += 1

    if pos_count == 0 or neg_count == 0:
        return (
            None,
            MLRankingStatus.UNAVAILABLE_SINGLE_CLASS,
            f"Training set has single class only ({pos_count} includes, {neg_count} excludes). Both classes required.",
            None,
        )

    # Check for empty text across samples
    non_empty = [t for t in texts if t]
    if not non_empty:
        return (
            None,
            MLRankingStatus.UNAVAILABLE_EMPTY_VOCAB,
            "All training records have empty text.",
            None,
        )

    try:
        vectorizer = TfidfVectorizer(
            max_features=config["max_features"],
            ngram_range=tuple(config["ngram_range"]),
            sublinear_tf=config["sublinear_tf"],
            stop_words=config["stop_words"],
        )
        classifier = LogisticRegression(
            class_weight=config["class_weight"],
            C=config["c_param"],
            random_state=config["seed"],
            max_iter=1000,
            solver="lbfgs",
        )
        pipe = Pipeline([
            ("vectorizer", vectorizer),
            ("classifier", classifier),
        ])

        pipe.fit(texts, labels)

        vocab_size = len(vectorizer.vocabulary_)
        if vocab_size == 0:
            return (
                None,
                MLRankingStatus.UNAVAILABLE_EMPTY_VOCAB,
                "Fitted vectorizer resulted in empty vocabulary.",
                None,
            )

        metadata = {
            "model_version": model_version,
            "feature_config": config,
            "train_record_count": len(train_records),
            "positive_count": pos_count,
            "negative_count": neg_count,
            "vocabulary_size": vocab_size,
            "sklearn_version": sklearn.__version__,
        }
        return pipe, MLRankingStatus.AVAILABLE, None, metadata

    except (ValueError, TypeError, KeyError, OSError, RuntimeError) as exc:
        return (
            None,
            MLRankingStatus.UNAVAILABLE_EMPTY_VOCAB,
            f"Model training error: {exc}",
            None,
        )


def save_model_artifact(
    pipeline: Pipeline,
    metadata: dict[str, Any],
    output_dir: Path,
) -> MLModelManifest:
    """Serialize fitted model and write signed metadata manifest with SHA-256."""
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "model.joblib"
    manifest_path = output_dir / "manifest.json"

    # Save model
    joblib.dump(pipeline, model_path, compress=3)

    # Calculate SHA-256
    sha256 = compute_file_sha256(model_path)

    manifest_dict = {
        "model_version": metadata.get("model_version", "classical_ranker:v1.0.0"),
        "artifact_sha256": sha256,
        "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "sklearn_version": metadata.get("sklearn_version", sklearn.__version__),
        "feature_config": metadata.get("feature_config", DEFAULT_FEATURE_CONFIG),
        "train_split_sha256": metadata.get("train_split_sha256", ""),
        "train_record_count": metadata.get("train_record_count", 0),
        "positive_count": metadata.get("positive_count", 0),
        "negative_count": metadata.get("negative_count", 0),
        "vocabulary_size": metadata.get("vocabulary_size", 0),
        "metrics": metadata.get("metrics", {}),
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_dict, f, indent=2)

    return MLModelManifest(**manifest_dict)


def load_model_artifact(
    artifact_dir: Path,
    expected_sha256: str | None = None,
) -> tuple[Pipeline | None, MLModelManifest | None, MLRankingStatus, str | None]:
    """Safely load model artifact verifying SHA-256 checksum and metadata."""
    model_path = artifact_dir / "model.joblib"
    manifest_path = artifact_dir / "manifest.json"

    if not model_path.exists() or not manifest_path.exists():
        return (
            None,
            None,
            MLRankingStatus.UNAVAILABLE_CORRUPT_ARTIFACT,
            f"Artifact files not found in {artifact_dir}.",
        )

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
        manifest = MLModelManifest(**manifest_data)
    except (ValueError, TypeError, KeyError, OSError, json.JSONDecodeError) as exc:
        return (
            None,
            None,
            MLRankingStatus.UNAVAILABLE_CORRUPT_ARTIFACT,
            f"Invalid manifest file: {exc}",
        )

    actual_sha256 = compute_file_sha256(model_path)
    if actual_sha256 != manifest.artifact_sha256:
        return (
            None,
            None,
            MLRankingStatus.UNAVAILABLE_CORRUPT_ARTIFACT,
            f"Checksum mismatch: expected {manifest.artifact_sha256}, got {actual_sha256}.",
        )

    if expected_sha256 and actual_sha256 != expected_sha256:
        return (
            None,
            None,
            MLRankingStatus.UNAVAILABLE_CORRUPT_ARTIFACT,
            f"Expected SHA256 {expected_sha256} does not match {actual_sha256}.",
        )

    try:
        pipeline = joblib.load(model_path)
        return pipeline, manifest, MLRankingStatus.AVAILABLE, None
    except (ValueError, TypeError, OSError, RuntimeError) as exc:
        return (
            None,
            None,
            MLRankingStatus.UNAVAILABLE_CORRUPT_ARTIFACT,
            f"Failed to load joblib model: {exc}",
        )


def score_and_rank_records(
    pipeline: Pipeline,
    records: list[MLRecordInput],
    model_version: str = "classical_ranker:v1.0.0",
    artifact_sha256: str | None = None,
) -> MLRankingResult:
    """Score records and sort descending by priority.
    
    Guarantees:
    - Pure callable: does not mutate input records or change database state.
    - Scores are prioritization suggestions, never automated exclusions.
    - Returns ranked list in [0.0, 1.0] range.
    """
    if not records:
        return MLRankingResult(
            status=MLRankingStatus.AVAILABLE,
            is_available=True,
            model_version=model_version,
            artifact_sha256=artifact_sha256,
            ranked_records=[],
        )

    texts = [extract_record_text(r) for r in records]
    try:
        # LogisticRegression.predict_proba returns [P(class=0), P(class=1)]
        probas = pipeline.predict_proba(texts)
        # Class 1 is INCLUDE
        scores = [float(p[1]) for p in probas]
    except (ValueError, TypeError, RuntimeError) as exc:
        return MLRankingResult(
            status=MLRankingStatus.UNAVAILABLE_CORRUPT_ARTIFACT,
            is_available=False,
            model_version=model_version,
            artifact_sha256=artifact_sha256,
            reason=f"Scoring failed: {exc}",
        )

    # Sort descending by score
    scored_items = list(zip([r.id for r in records], scores))
    scored_items.sort(key=lambda x: x[1], reverse=True)

    ranked_records = [
        RankedRecord(record_id=rec_id, score=round(sc, 4), rank=idx + 1)
        for idx, (rec_id, sc) in enumerate(scored_items)
    ]

    return MLRankingResult(
        status=MLRankingStatus.AVAILABLE,
        is_available=True,
        model_version=model_version,
        artifact_sha256=artifact_sha256,
        ranked_records=ranked_records,
    )
