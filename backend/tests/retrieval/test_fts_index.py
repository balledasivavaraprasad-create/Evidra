"""Unit tests for in-memory SQLite FTS5 search index and query escaping (C06)."""
from app.retrieval.index import (
    CorpusFTSCache,
    InMemoryCorpusFTSIndex,
    escape_fts_query,
)


def test_escape_fts_query_removes_dangerous_operators():
    """Quotes, asterisks, colons, brackets, and SQL/FTS operators are sanitized."""
    raw = 'metformin* AND "placebo" OR NOT NEAR: (adults) [RCT]'
    escaped = escape_fts_query(raw)
    # Special characters removed and terms wrapped in quotes
    assert "*" not in escaped
    assert ":" not in escaped
    assert "NEAR" not in escaped
    assert '"metformin"' in escaped
    assert '"placebo"' in escaped
    assert '"adults"' in escaped


def test_escape_fts_query_empty_or_whitespace():
    assert escape_fts_query("") == ""
    assert escape_fts_query("   ") == ""
    assert escape_fts_query('*** ::: """') == ""


def test_in_memory_fts_index_population_and_search():
    """Populate index with records and search returning verified RetrievalChunks."""
    index = InMemoryCorpusFTSIndex(workspace_id="ws-1", corpus_revision_id="rev-1")

    records = [
        {
            "id": "rec-1",
            "source_record_id": "src-1",
            "title": "Randomized trial of semaglutide in type 2 diabetes",
            "abstract_text": "A double-blind study evaluating semaglutide versus placebo in adult diabetics.",
            "content_hash": "hash1",
        },
        {
            "id": "rec-2",
            "source_record_id": "src-2",
            "title": "Observational cohort of pediatric asthma",
            "abstract_text": "Children aged 5-10 were assessed for respiratory symptoms.",
            "content_hash": "hash2",
        },
    ]

    index.populate(records)
    assert index.indexed_records == 2

    # Search for diabetes
    chunks = index.search("semaglutide diabetes")
    assert len(chunks) == 1
    assert chunks[0].record_revision_id == "rec-1"
    assert chunks[0].source_record_id == "src-1"
    assert chunks[0].citation_handle == "[src-1]"

    # Search for asthma
    asthma_chunks = index.search("asthma")
    assert len(asthma_chunks) == 1
    assert asthma_chunks[0].record_revision_id == "rec-2"

    # Search with no match
    no_match = index.search("oncology neoplasm chemotherapy")
    assert len(no_match) == 0

    index.close()


def test_fts_cache_invalidation():
    """Cache stores, retrieves, and invalidates in-memory indices by workspace."""
    cache = CorpusFTSCache()
    idx1 = InMemoryCorpusFTSIndex(workspace_id="ws-A", corpus_revision_id="rev-1")
    idx2 = InMemoryCorpusFTSIndex(workspace_id="ws-B", corpus_revision_id="rev-2")

    cache.put(idx1)
    cache.put(idx2)

    assert cache.get("ws-A", "rev-1") is idx1
    assert cache.get("ws-B", "rev-2") is idx2

    # Invalidate ws-A
    cache.invalidate(workspace_id="ws-A")
    assert cache.get("ws-A", "rev-1") is None
    assert cache.get("ws-B", "rev-2") is idx2

    cache.invalidate(workspace_id="ws-B")
    assert cache.get("ws-B", "rev-2") is None
