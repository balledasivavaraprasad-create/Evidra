"""Evidence retrieval and FTS search module (C06)."""
from app.retrieval.index import (
    GLOBAL_FTS_CACHE,
    CorpusFTSCache,
    InMemoryCorpusFTSIndex,
    escape_fts_query,
)

__all__ = [
    "GLOBAL_FTS_CACHE",
    "CorpusFTSCache",
    "InMemoryCorpusFTSIndex",
    "escape_fts_query",
]
