"""Type definitions for classical ML screening prioritization (B05)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MLRankingStatus(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE_INSUFFICIENT_DATA = "unavailable_insufficient_data"
    UNAVAILABLE_SINGLE_CLASS = "unavailable_single_class"
    UNAVAILABLE_EMPTY_VOCAB = "unavailable_empty_vocab"
    UNAVAILABLE_CORRUPT_ARTIFACT = "unavailable_corrupt_artifact"
    UNAVAILABLE_DISABLED = "unavailable_disabled"


@dataclass(frozen=True)
class MLRecordInput:
    """Input record for ML ranking."""
    id: str
    title: str
    abstract: str
    label: str | None = None  # "INCLUDE" or "EXCLUDE" if known (for training/evaluation)


@dataclass(frozen=True)
class RankedRecord:
    """A scored record with priority score for screening order."""
    record_id: str
    score: float  # Score in [0.0, 1.0]; higher indicates higher priority for inclusion review
    rank: int


@dataclass
class MLRankingResult:
    """Result of ML ranking callable."""
    status: MLRankingStatus
    is_available: bool
    model_version: str | None = None
    artifact_sha256: str | None = None
    ranked_records: list[RankedRecord] = field(default_factory=list)
    reason: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MLModelManifest:
    """Metadata manifest accompanying a saved ML ranking artifact."""
    model_version: str
    artifact_sha256: str
    created_at: str
    sklearn_version: str
    feature_config: dict[str, Any]
    train_split_sha256: str
    train_record_count: int
    positive_count: int
    negative_count: int
    vocabulary_size: int
    metrics: dict[str, float]
