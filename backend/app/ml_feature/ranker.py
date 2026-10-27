"""Runtime inference, artifact verification, and deterministic queue ranking."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
from sklearn.pipeline import Pipeline

from app.ml_feature.dataset import prepare_text
from app.ml_feature.trainer import compute_file_sha256
from app.ml_feature.types import (
    ArtifactManifest,
    RankingBatch,
    RankingContext,
    RankingItem,
)


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
    actual_sha256 = compute_file_sha256(model_path)
    if actual_sha256 != manifest.model_file_sha256:
        raise ValueError(
            f"Artifact integrity check failed: model file SHA-256 ({actual_sha256}) "
            f"does not match manifest checksum ({manifest.model_file_sha256})"
        )

    pipeline: Pipeline = joblib.load(model_path)
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

        probs = self.pipeline.predict_proba([text])
        # Probability of class 1 (priority / include)
        return float(round(probs[0, 1], 4))

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

        candidate_items: list[tuple[float, str, str, str | None]] = []
        for r in records:
            rid = str(getattr(r, "id", ""))
            title = getattr(r, "title", "")
            abstract = getattr(r, "abstract_text", None)

            if abstract is None or len(abstract.strip()) < 10:
                candidate_items.append((0.0, rid, "UNAVAILABLE", "MISSING_ABSTRACT"))
            else:
                score = self.predict_score(title, abstract)
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
