"""High-level ML screening ranker service (B05)."""
from __future__ import annotations

from pathlib import Path

from app.screening.ml.pipeline import (
    load_model_artifact,
    score_and_rank_records,
)
from app.screening.ml.types import (
    MLModelManifest,
    MLRankingResult,
    MLRankingStatus,
    MLRecordInput,
    RankedRecord,
)


class MLScreeningRanker:
    """Optional classical ML ranking engine.
    
    Invariants:
    - Never changes stored eligibility decisions or human events.
    - Scores are uncalibrated prioritization aids, not clinical probabilities.
    - If artifact is missing, unverified, or disabled, returns typed unavailable result.
    """

    def __init__(
        self,
        artifact_dir: Path | None = None,
        enabled: bool = True,
        expected_sha256: str | None = None,
    ) -> None:
        self.enabled = enabled
        self.artifact_dir = artifact_dir
        self.expected_sha256 = expected_sha256
        self.pipeline = None
        self.manifest: MLModelManifest | None = None
        self.status = MLRankingStatus.AVAILABLE if enabled else MLRankingStatus.UNAVAILABLE_DISABLED
        self.reason: str | None = None

        if self.enabled and self.artifact_dir:
            self._load()

    def _load(self) -> None:
        if not self.artifact_dir:
            return
        pipe, manifest, status, err = load_model_artifact(
            self.artifact_dir, expected_sha256=self.expected_sha256
        )
        self.pipeline = pipe
        self.manifest = manifest
        self.status = status
        self.reason = err

    def rank(self, records: list[MLRecordInput]) -> MLRankingResult:
        """Rank input records for screening priority."""
        if not self.enabled:
            return MLRankingResult(
                status=MLRankingStatus.UNAVAILABLE_DISABLED,
                is_available=False,
                reason="Classical ML ranking is disabled in runtime configuration.",
            )

        if self.status != MLRankingStatus.AVAILABLE or self.pipeline is None:
            return MLRankingResult(
                status=self.status,
                is_available=False,
                reason=self.reason or "ML model artifact is not loaded.",
            )

        model_version = self.manifest.model_version if self.manifest else "classical_ranker:v1.0.0"
        artifact_sha256 = self.manifest.artifact_sha256 if self.manifest else None

        return score_and_rank_records(
            pipeline=self.pipeline,
            records=records,
            model_version=model_version,
            artifact_sha256=artifact_sha256,
        )


def compute_recall_at_k(
    ranked_records: list[RankedRecord],
    ground_truth_includes: set[str],
    k: int,
) -> float:
    """Compute Recall@k: fraction of included studies found in top k records."""
    if not ground_truth_includes:
        return 1.0
    top_k = ranked_records[:k]
    top_k_ids = {r.record_id for r in top_k}
    hits = len(top_k_ids.intersection(ground_truth_includes))
    return hits / len(ground_truth_includes)


def compute_work_saved_at_recall(
    ranked_records: list[RankedRecord],
    ground_truth_includes: set[str],
    target_recall: float = 0.95,
) -> tuple[float, int]:
    """Calculate Work Saved at Recall (e.g., WSS@95).
    
    Formula: WSS@R = (N - n) / N - (1 - R)
    where N is total records, n is records screened to achieve target recall R.
    Returns: (wss_score, cutoff_n)
    """
    total_n = len(ranked_records)
    total_relevant = len(ground_truth_includes)

    if total_n == 0 or total_relevant == 0:
        return 0.0, 0

    hits = 0
    cutoff_n = total_n

    for i, r in enumerate(ranked_records):
        if r.record_id in ground_truth_includes:
            hits += 1
            current_recall = hits / total_relevant
            if current_recall >= target_recall:
                cutoff_n = i + 1
                break

    actual_recall = hits / total_relevant
    if actual_recall < target_recall:
        cutoff_n = total_n

    # Fraction of corpus screened:
    screened_ratio = cutoff_n / total_n
    # WSS@R formula
    wss = (1.0 - screened_ratio) - (1.0 - target_recall)
    return round(wss, 4), cutoff_n
