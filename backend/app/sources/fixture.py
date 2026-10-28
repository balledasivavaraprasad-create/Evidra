"""Test-only fixture transport delivering deterministic synthetic literature responses."""
import hashlib
from datetime import UTC, datetime

from app.contracts.enums import JobState, SourceNamespace
from app.contracts.models import (
    RecordRevisionResponse,
    SearchExecutionResponse,
)
from tests.fixtures.synthetic_records import ALL_SYNTHETIC_RECORDS


def get_fixture_search_count(
    query_version_id: str,
    source: SourceNamespace,
    exact_query: str,
    cap: int | None = None,
    synonym_expansion: bool = False,
) -> SearchExecutionResponse:
    """Return deterministic synthetic count matching query."""
    matching_records = [
        r for r in ALL_SYNTHETIC_RECORDS
        if r["source"] == source.value
    ]
    hit_count = len(matching_records)
    if hit_count == 0:
        hit_count = len(ALL_SYNTHETIC_RECORDS)

    raw_hash = hashlib.sha256(f"fixture-{source.value}-{exact_query}".encode()).hexdigest()

    return SearchExecutionResponse(
        id=f"exec-fixture-{source.value}-{hashlib.sha256((query_version_id + exact_query).encode()).hexdigest()[:12]}",
        query_version_id=query_version_id,
        source=source,
        exact_query=exact_query,
        synonym_setting=synonym_expansion,
        hit_count=hit_count,
        counted_at=datetime.now(UTC),
        status=JobState.SUCCEEDED,
        partial=False,
        cap=cap,
        raw_hash=raw_hash,
    )


def get_fixture_ids(source: SourceNamespace, retmax: int = 200, retstart: int = 0) -> list[str]:
    """Return synthetic PMIDs / IDs list."""
    matching = [
        r["external_id"]
        for r in ALL_SYNTHETIC_RECORDS
        if r["source"] == source.value
    ]
    if not matching:
        matching = [r["external_id"] for r in ALL_SYNTHETIC_RECORDS]
    return matching[retstart : retstart + retmax]


def get_fixture_records(source: SourceNamespace, ids: list[str]) -> list[RecordRevisionResponse]:
    """Return normalized RecordRevisionResponse objects matching requested IDs."""
    results = []
    id_set = set(ids)
    for raw in ALL_SYNTHETIC_RECORDS:
        if raw["external_id"] in id_set:
            results.append(RecordRevisionResponse.model_validate(raw))
    return results


def get_fixture_page(
    source: SourceNamespace,
    cursor: str = "*",
    page_size: int = 50,
) -> tuple[list[RecordRevisionResponse], str | None]:
    """Return a single page of fixture records with simulated cursor progression."""
    all_recs = [
        RecordRevisionResponse.model_validate(r)
        for r in ALL_SYNTHETIC_RECORDS
        if r["source"] == source.value
    ]
    if not all_recs:
        all_recs = [RecordRevisionResponse.model_validate(r) for r in ALL_SYNTHETIC_RECORDS]

    # Simple cursor simulation: cursor is page index '1', '2', etc.
    page_idx = 0 if cursor == "*" else int(cursor)
    start = page_idx * page_size
    end = start + page_size
    page_items = all_recs[start:end]

    next_cursor = str(page_idx + 1) if end < len(all_recs) else None
    return page_items, next_cursor
