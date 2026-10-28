"""Typed State definitions for Evidra durable LangGraph review orchestration."""
from __future__ import annotations

from typing import Any, TypedDict

GRAPH_VERSION = "review_graph:v2.0.0"
SUPPORTED_GRAPH_VERSIONS = {"review_graph:v1.0.0", "review_graph:v2.0.0"}


class ReviewGraphState(TypedDict):
    """Immutable, bounded graph state for review orchestration.

    Does NOT store full literature abstract texts in graph state to avoid
    memory explosion during SQLite checkpoint serialization. Keeps identifiers,
    counts, fingerprints, and bounded review flags.
    """

    workspace_id: str
    job_id: str | None
    criteria_version_id: str | None
    corpus_revision_id: str | None
    group_count: int
    record_count: int
    included_count: int
    excluded_count: int
    uncertain_count: int
    stage: str
    pending_human_review: dict[str, Any] | None
    human_approved: bool
    human_event_id: str | None
    error: str | None
    trace_steps: list[str]
    graph_version: str

    # C04 incremental & snapshot-aware extensions
    mode: str  # "full" | "incremental" | "restore"
    restore_snapshot_id: str | None
    reused_screening_count: int
    recomputed_screening_count: int
    reused_pico_count: int
    recomputed_pico_count: int
    invalidation_fingerprint: str | None
    affected_group_ids: list[str]
