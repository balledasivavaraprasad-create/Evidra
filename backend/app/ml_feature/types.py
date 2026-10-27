"""Data types and schemas for Evidra machine learning review prioritization feature."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RecordInput(BaseModel):
    """Normalized literature record representation for ML processing."""

    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    abstract_text: str | None = None
    group_id: str | None = None
    label: int | None = None  # 1 for priority/include, 0 for exclude


class TrainConfig(BaseModel):
    """Hyperparameter and resource configuration for ML pipeline training."""

    model_config = ConfigDict(extra="forbid")

    max_features: int = Field(default=1000, ge=50, le=10000, description="Max vocabulary size")
    ngram_min: int = Field(default=1, ge=1, le=3)
    ngram_max: int = Field(default=2, ge=1, le=3)
    c_param: float = Field(default=1.0, gt=0.0, description="L2 regularization inverse strength")
    class_weight: str = Field(default="balanced", description="'balanced' or None")
    seed: int = Field(default=42, description="Deterministic pseudo-random seed")
    val_ratio: float = Field(default=0.2, ge=0.05, le=0.4)
    test_ratio: float = Field(default=0.2, ge=0.05, le=0.4)


class ArtifactManifest(BaseModel):
    """Cryptographic provenance and runtime metadata for a trained ranker artifact."""

    model_config = ConfigDict(extra="forbid")

    artifact_version: str = Field(description="Semantic version tag, e.g. ml_ranker:v1.0.0")
    model_type: str = Field(default="Tfidf_LogisticRegression")
    sklearn_version: str
    joblib_version: str
    created_at: str
    scope: str = Field(description="Target review question/criteria identifier")
    feature_count: int
    train_records_count: int
    train_hash: str
    val_hash: str
    test_hash: str
    model_file_sha256: str
    config: dict[str, Any]
    metrics: dict[str, float] = Field(default_factory=dict)


class RankingItem(BaseModel):
    """Prioritization prediction for an individual literature record."""

    model_config = ConfigDict(extra="forbid")

    record_id: str
    score: float = Field(ge=0.0, le=1.0, description="Model priority score; higher = prioritize review")
    rank: int = Field(ge=1, description="1-based queue order after tie breaking")
    state: str = Field(description="'SCORED', 'UNAVAILABLE', or 'OUT_OF_SCOPE'")
    reason: str | None = None


class RankingBatch(BaseModel):
    """Collection of prioritized records returned by the ranker."""

    model_config = ConfigDict(extra="forbid")

    scope: str
    model_version: str
    total_records: int
    scored_count: int
    items: list[RankingItem]
    ranked_at: str


class RankingContext(BaseModel):
    """Inference scope and boundary context for record ranking."""

    model_config = ConfigDict(extra="forbid")

    review_question: str
    criteria_version_id: str | None = None
    threshold: float = Field(default=0.5, ge=0.0, le=1.0)
