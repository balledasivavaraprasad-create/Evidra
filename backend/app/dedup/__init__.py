"""Deduplication package exporting DeduplicationEngine adhering to DeduplicationPort."""
from __future__ import annotations

from typing import Any

from app.contracts.models import DedupProposal, RecordRevisionResponse
from app.contracts.ports import DeduplicationPort
from app.dedup.matcher import find_candidate_pairs
from app.dedup.partitioner import partition_groups, select_group_representative


class DeduplicationEngine(DeduplicationPort):
    """Pure, deterministic deduplication engine implemented by dev-B (B01)."""

    def find_candidate_pairs(
        self,
        records: list[RecordRevisionResponse],
    ) -> list[DedupProposal]:
        """Detect duplicate candidate pairs deterministically across given records."""
        return find_candidate_pairs(records)

    def partition_groups(
        self,
        records: list[RecordRevisionResponse],
        accepted_edges: list[DedupProposal],
        cannot_link_pairs: set[tuple[str, str]] | None = None,
    ) -> list[dict[str, Any]]:
        """Group records into connected components obeying cannot-link constraints."""
        return partition_groups(records, accepted_edges, cannot_link_pairs)


__all__ = [
    "DeduplicationEngine",
    "find_candidate_pairs",
    "partition_groups",
    "select_group_representative",
]
