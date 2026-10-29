"""Runtime inference, artifact verification, and deterministic queue ranking."""
from __future__ import annotations

import hashlib
import io
import json
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import sklearn
from sklearn.pipeline import Pipeline

from app.ml_feature.dataset import prepare_text
from app.ml_feature.types import (
    ArtifactManifest,
    RankingBatch,
    RankingContext,
    RankingItem,
    RecordInput,
)


@lru_cache(maxsize=4)
def _deserialize_verified(model_bytes: bytes) -> Pipeline:
    """Only called after validation, for deployment-owned local artifacts."""
    return joblib.load(io.BytesIO(model_bytes))


def load_ranker(
    artifact_dir: Path | str,
    expected_scope: str | None = None,
) -> MLRanker:
    """Load a verified, tamper-checked MLRanker from a local artifact directory.

    Strict security checks:
    - Reads manifest.json and confirms matching review scope.
    - Recalculates model.joblib SHA-256 checksum and compares against manifest.
    - Rejects tampered, corrupt, or mismatched models before executing deserialization.
    """
    path = Path(artifact_dir)
    manifest_path = path / "manifest.json"
    model_path = path / "model.joblib"

    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing artifact manifest at {manifest_path}")
    if not model_path.exists():
        raise FileNotFoundError(f"Missing model binary at {model_path}")

    with open(manifest_path, encoding="utf-8") as f:
        manifest_data = json.load(f)

    manifest = ArtifactManifest(**manifest_data)

    # 1. Scope verification
    if expected_scope is not None and manifest.scope != expected_scope:
        raise ValueError(
            f"Artifact scope mismatch: model scope '{manifest.scope}' does not match expected '{expected_scope}'"
        )

    # 2. Checksum tamper verification
    if model_path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError("Model exceeds the 64 MiB artifact bound")
    model_bytes = model_path.read_bytes()
    actual_sha256 = hashlib.sha256(model_bytes).hexdigest()
    if actual_sha256 != manifest.model_file_sha256:
        raise ValueError(
            f"Artifact integrity check failed: model file SHA-256 ({actual_sha256}) "
            f"does not match manifest checksum ({manifest.model_file_sha256})"
        )

    if manifest.sklearn_version != sklearn.__version__:
        raise ValueError("Artifact sklearn version is incompatible with this runtime")
    if manifest.config.get("input_schema", "text-v1") not in {"text-v1", "heterogeneous-v1"}:
        raise ValueError("Unsupported artifact input schema")
    pipeline = _deserialize_verified(model_bytes)
    return MLRanker(pipeline=pipeline, manifest=manifest)


class MLRanker:
    """Deterministic inference engine prioritizing literature records for review."""

    def __init__(self, pipeline: Pipeline, manifest: ArtifactManifest) -> None:
        self.pipeline = pipeline
        self.manifest = manifest

    def predict_score(self, title: str, abstract_text: str | None) -> float:
        """Predict continuous review priority score [0.0, 1.0] for a single title + abstract."""
        text = prepare_text(title, abstract_text)
        if not text:
            return 0.0

        return self.predict_records([RecordInput(id="single", title=title, abstract_text=abstract_text)])[0]

    def predict_records(self, records: list[RecordInput]) -> list[float]:
        """Bounded batch scoring, without rounding before queue ordering."""
        classes = list(self.pipeline.classes_)
        if 1 not in classes:
            raise ValueError("Artifact has no positive class")
        results: list[float] = []
        for start in range(0, len(records), 256):
            batch = records[start:start + 256]
            if self.manifest.config.get("input_schema") == "heterogeneous-v1":
                from app.ml_feature.advanced import feature_rows
                inputs = feature_rows(batch)
            else:
                inputs = [prepare_text(r.title[:50000], (r.abstract_text or "")[:50000]) for r in batch]
            scores = np.asarray(self.pipeline.predict_proba(inputs))[:, classes.index(1)]
            if not np.isfinite(scores).all() or (scores < 0).any() or (scores > 1).any():
                raise ValueError("Invalid model scores")
            results.extend(float(score) for score in scores)
        return results

    def rank_records(
        self,
        records: list[Any],
        context: RankingContext,
    ) -> RankingBatch:
        """Rank a batch of records deterministically by review priority score.

        Invariants:
        - Missing abstracts yield state='UNAVAILABLE' and score=0.0 with reason='MISSING_ABSTRACT'.
        - Equal scores are broken deterministically using record ID.
        - Records are never mutated in place.
        """
        if context.review_question != self.manifest.scope:
            # Context mismatch: mark all items OUT_OF_SCOPE
            items = [
                RankingItem(
                    record_id=str(getattr(r, "id", f"rec_{idx}")),
                    score=0.0,
                    rank=idx + 1,
                    state="OUT_OF_SCOPE",
                    reason=f"Model scope '{self.manifest.scope}' differs from request '{context.review_question}'",
                )
                for idx, r in enumerate(records)
            ]
            return RankingBatch(
                scope=context.review_question,
                model_version=self.manifest.artifact_version,
                total_records=len(records),
                scored_count=0,
                items=items,
                ranked_at=datetime.now(UTC).isoformat(),
            )

        valid = [r for r in records if getattr(r, "abstract_text", None)
                 and len(r.abstract_text.strip()) >= 10]
        scores = dict(zip((r.id for r in valid), self.predict_records(valid), strict=True))
        candidate_items: list[tuple[float, str, str, str | None]] = []
        for r in records:
            rid = str(getattr(r, "id", ""))
            abstract = getattr(r, "abstract_text", None)

            if abstract is None or len(abstract.strip()) < 10:
                candidate_items.append((0.0, rid, "UNAVAILABLE", "MISSING_ABSTRACT"))
            else:
                score = scores[rid]
                candidate_items.append((score, rid, "SCORED", None))

        # Sort descending by score, tie-break ascending by record_id
        candidate_items.sort(key=lambda x: (-x[0], x[1]))

        ranked_items = [
            RankingItem(
                record_id=rid,
                score=score,
                rank=idx + 1,
                state=state,
                reason=reason,
            )
            for idx, (score, rid, state, reason) in enumerate(candidate_items)
        ]

        scored_count = sum(1 for item in ranked_items if item.state == "SCORED")

        return RankingBatch(
            scope=self.manifest.scope,
            model_version=self.manifest.artifact_version,
            total_records=len(records),
            scored_count=scored_count,
            items=ranked_items,
            ranked_at=datetime.now(UTC).isoformat(),
        )
