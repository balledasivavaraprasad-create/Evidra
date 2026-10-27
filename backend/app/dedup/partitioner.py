"""Deterministic connected component partitioning and representative selection."""
from __future__ import annotations

from typing import Any

from app.contracts.models import DedupProposal, RecordRevisionResponse


def select_group_representative(records: list[RecordRevisionResponse]) -> RecordRevisionResponse:
    """Deterministically select the best representative record for a paper group.

    Selection priority:
    1. Richness of content: non-empty abstract text preferred over missing.
    2. Metadata completeness: count of non-null metadata attributes (DOI, journal, pages, year).
    3. Source preference: PubMed prioritized for canonical medical indexing.
    4. Stable tie-breaker: alphabetical minimum of record ID.
    Never uses arrival order or wall-clock time.
    """
    if not records:
        raise ValueError("Cannot select representative from an empty record list")

    if len(records) == 1:
        return records[0]

    def score_key(rec: RecordRevisionResponse) -> tuple[int, int, int, str]:
        # 1. Has non-empty abstract
        has_abstract = 1 if (rec.abstract_text and rec.abstract_text.strip()) else 0

        # 2. Metadata completeness score
        completeness = 0
        if rec.doi:
            completeness += 2
        if rec.pmid:
            completeness += 2
        if rec.journal:
            completeness += 1
        if rec.pages:
            completeness += 1
        if rec.year:
            completeness += 1
        if rec.publication_types:
            completeness += 1

        # 3. Source priority
        source_val = 2 if rec.source == "pubmed" else (1 if rec.source == "europepmc" else 0)

        # 4. Tie-breaker: reverse record ID because sort is descending
        # For the tie breaker, we want alphabetical minimum, so we use string inversion or separate key
        return (has_abstract, completeness, source_val, rec.id)

    # Sort candidates deterministically
    # To get maximum score and alphabetical minimum id:
    candidates = sorted(
        records,
        key=lambda r: (
            -(1 if (r.abstract_text and r.abstract_text.strip()) else 0),
            -sum([bool(r.doi) * 2, bool(r.pmid) * 2, bool(r.journal), bool(r.pages), bool(r.year), bool(r.publication_types)]),
            -(2 if r.source == "pubmed" else (1 if r.source == "europepmc" else 0)),
            r.id,
        ),
    )
    return candidates[0]


def partition_groups(
    records: list[RecordRevisionResponse],
    accepted_edges: list[DedupProposal],
    cannot_link_pairs: set[tuple[str, str]] | None = None,
) -> list[dict[str, Any]]:
    """Group records into connected components obeying cannot-link constraints.

    Returns a deterministically ordered list of group summaries with
    selected representatives, member IDs, and member objects.
    """
    if not records:
        return []

    # Map records by ID
    by_id = {r.id: r for r in records}
    normalized_cannot_link: set[tuple[str, str]] = set()
    if cannot_link_pairs:
        for u, v in cannot_link_pairs:
            normalized_cannot_link.add((u, v))
            normalized_cannot_link.add((v, u))

    # Union-Find data structure with cannot-link validation
    parent = {r.id: r.id for r in records}

    def find(x: str) -> str:
        path = []
        while parent[x] != x:
            path.append(x)
            x = parent[x]
        for node in path:
            parent[node] = x
        return x

    def can_merge(root_u: str, root_v: str, component_map: dict[str, set[str]]) -> bool:
        members_u = component_map[root_u]
        members_v = component_map[root_v]
        for mu in members_u:
            for mv in members_v:
                if (mu, mv) in normalized_cannot_link:
                    return False
        return True

    # Initialize components
    components: dict[str, set[str]] = {r.id: {r.id} for r in records}

    # Process accepted edges deterministically sorted by score descending, then IDs
    sorted_edges = sorted(
        accepted_edges,
        key=lambda e: (-e.score, e.record_id_a, e.record_id_b),
    )

    for edge in sorted_edges:
        if edge.record_id_a not in by_id or edge.record_id_b not in by_id:
            continue

        root_a = find(edge.record_id_a)
        root_b = find(edge.record_id_b)

        if root_a != root_b and can_merge(root_a, root_b, components):
            # Merge root_b into root_a
            parent[root_b] = root_a
            components[root_a].update(components[root_b])
            del components[root_b]

    # Collect final components
    final_groups: list[dict[str, Any]] = []
    for member_id_set in components.values():
        member_records = [by_id[mid] for mid in sorted(member_id_set)]
        rep = select_group_representative(member_records)
        sorted_mids = [r.id for r in member_records]

        final_groups.append(
            {
                "group_id": f"grp-{rep.id}",
                "representative": rep,
                "member_ids": sorted_mids,
                "members": member_records,
                "member_count": len(member_records),
                "is_singleton": len(member_records) == 1,
            }
        )

    # Sort groups deterministically by representative ID
    return sorted(final_groups, key=lambda g: g["representative"].id)
