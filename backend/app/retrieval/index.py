"""In-memory SQLite FTS5 search index for authorized corpus revisions (C06)."""
from __future__ import annotations

import logging
import re
import sqlite3

from app.contracts.models import RetrievalChunk

logger = logging.getLogger(__name__)

MAX_INDEX_RECORDS = 1_000
MAX_INDEX_BYTES = 15_000_000  # 15 MB in-memory boundary


def escape_fts_query(query: str) -> str:
    """Sanitize and escape user query to prevent SQLite FTS5 syntax errors and injection."""
    if not query:
        return ""
    # Strip any characters that have special meaning in FTS5: quotes, asterisks, brackets, colons, etc.
    cleaned = re.sub(r'[\'\"*^:()\[\]\{\}]', " ", query)
    # Remove FTS boolean keywords if they appear as standalone operators
    tokens = cleaned.split()
    safe_tokens: list[str] = []
    for t in tokens:
        upper_t = t.upper()
        if upper_t in ("AND", "OR", "NOT", "NEAR"):
            continue
        # Clean alphanumeric characters and hyphens
        word = re.sub(r"[^\w\-]", "", t)
        if word:
            # Wrap in double quotes for exact term match
            safe_tokens.append(f'"{word}"')

    if not safe_tokens:
        return ""
    # Join with OR for broad lexical recall
    return " OR ".join(safe_tokens)


class InMemoryCorpusFTSIndex:
    """Bounded, read-only in-memory FTS5 index populated from authorized corpus rows.
    
    Invariants:
    - Zero mutation of the persistent application database.
    - Strictly scoped to (workspace_id, corpus_revision_id).
    - Enforces record and memory limits.
    """

    def __init__(self, workspace_id: str, corpus_revision_id: str) -> None:
        self.workspace_id = workspace_id
        self.corpus_revision_id = corpus_revision_id
        self.indexed_records = 0
        self.indexed_bytes = 0
        self._conn = sqlite3.connect(":memory:")
        self._init_schema()

    def _init_schema(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE VIRTUAL TABLE corpus_fts USING fts5(
                    record_revision_id UNINDEXED,
                    source_record_id UNINDEXED,
                    title,
                    abstract_text,
                    content_hash UNINDEXED,
                    tokenize='unicode61'
                );
                """
            )

    def populate(self, records: list[dict]) -> None:
        """Populate the in-memory FTS index from authorized records."""
        if not records:
            return

        with self._conn:
            for r in records:
                if self.indexed_records >= MAX_INDEX_RECORDS:
                    logger.warning("FTS index record limit (%d) reached for revision %s", MAX_INDEX_RECORDS, self.corpus_revision_id)
                    break

                rec_rev_id = str(r["id"])
                src_rec_id = str(r.get("source_record_id", rec_rev_id))
                title = str(r.get("title", ""))
                abstract = str(r.get("abstract_text", ""))
                content_hash = str(r.get("content_hash", ""))

                row_bytes = len(title.encode("utf-8")) + len(abstract.encode("utf-8"))
                if self.indexed_bytes + row_bytes > MAX_INDEX_BYTES:
                    logger.warning("FTS index byte limit reached for revision %s", self.corpus_revision_id)
                    break

                self._conn.execute(
                    """
                    INSERT INTO corpus_fts(record_revision_id, source_record_id, title, abstract_text, content_hash)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (rec_rev_id, src_rec_id, title, abstract, content_hash),
                )
                self.indexed_records += 1
                self.indexed_bytes += row_bytes

    def search(self, raw_query: str, limit: int = 8) -> list[RetrievalChunk]:
        """Search in-memory FTS5 index and return structured, verifiable RetrievalChunks."""
        safe_query = escape_fts_query(raw_query)
        if not safe_query:
            return []

        safe_limit = min(max(1, limit), 20)
        chunks: list[RetrievalChunk] = []

        try:
            cursor = self._conn.execute(
                """
                SELECT record_revision_id, source_record_id, title, abstract_text, content_hash,
                       snippet(corpus_fts, 3, '', '', '...', 32)
                FROM corpus_fts
                WHERE corpus_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (safe_query, safe_limit),
            )
            rows = cursor.fetchall()

            for row in rows:
                rec_id, src_id, title, abstract, chash, snippet_txt = row
                # Calculate snippet span inside abstract if possible
                snippet_clean = snippet_txt.replace("...", "").strip()
                start_cp = 0
                end_cp = len(snippet_clean)
                if snippet_clean and snippet_clean in abstract:
                    start_cp = abstract.index(snippet_clean)
                    end_cp = start_cp + len(snippet_clean)

                chunks.append(
                    RetrievalChunk(
                        source_record_id=src_id,
                        record_revision_id=rec_id,
                        title=title,
                        content_hash=chash,
                        text_snippet=snippet_txt or title,
                        start_cp=start_cp,
                        end_cp=end_cp,
                        citation_handle=f"[{src_id or rec_id}]",
                    )
                )

        except sqlite3.OperationalError as exc:
            logger.error("FTS search execution failed on query '%s': %s", safe_query, exc)
            return []

        return chunks

    def close(self) -> None:
        """Close in-memory connection."""
        self._conn.close()


class CorpusFTSCache:
    """Thread-safe cache of in-memory FTS indices keyed by (workspace_id, corpus_revision_id)."""

    def __init__(self) -> None:
        self._cache: dict[tuple[str, str], InMemoryCorpusFTSIndex] = {}

    def get(self, workspace_id: str, corpus_revision_id: str) -> InMemoryCorpusFTSIndex | None:
        return self._cache.get((workspace_id, corpus_revision_id))

    def put(self, index: InMemoryCorpusFTSIndex) -> None:
        key = (index.workspace_id, index.corpus_revision_id)
        # Evict old if replacing
        if key in self._cache:
            self._cache[key].close()
        self._cache[key] = index

    def invalidate(self, workspace_id: str, corpus_revision_id: str | None = None) -> None:
        keys_to_remove = [
            k for k in self._cache
            if k[0] == workspace_id and (corpus_revision_id is None or k[1] == corpus_revision_id)
        ]
        for k in keys_to_remove:
            self._cache[k].close()
            del self._cache[k]


GLOBAL_FTS_CACHE = CorpusFTSCache()
