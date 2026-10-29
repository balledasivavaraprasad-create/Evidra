"""Authorized read-only evidence retrieval repository conforming to EvidenceRetrievalPort."""
from __future__ import annotations

import logging
import re

from sqlalchemy.orm import Session

from app.contracts.models import RetrievalChunk
from app.contracts.ports import EvidenceRetrievalPort
from app.db.models import (
    CorpusMemberModel,
    CorpusRevisionModel,
    GroupSnapshotModel,
    RecordRevisionModel,
    SourceRecordModel,
)
from app.terms import STOP_WORDS

logger = logging.getLogger(__name__)

# The most corpus members considered for one question; keeps retrieval bounded
CANDIDATE_LIMIT = 300
_WORD_RE = re.compile(r"[a-z0-9][a-z0-9\-]{2,}")


def _query_words(query: str) -> set[str]:
    return {w for w in _WORD_RE.findall(query.lower()) if w not in STOP_WORDS and not w.isdigit()}


def _overlap_score(words: set[str], title: str | None, abstract: str | None) -> int:
    """How many of the question's words the paper uses; title words count double."""
    if not words:
        return 0
    title_words = set(_WORD_RE.findall((title or "").lower()))
    abstract_words = set(_WORD_RE.findall((abstract or "").lower()))
    return sum(2 for w in words if w in title_words) + sum(1 for w in words if w in abstract_words)


class SqliteEvidenceRepository(EvidenceRetrievalPort):
    """Authorized read-only evidence retrieval repository for bounded RAG and assistant workflows.

    Enforces workspace isolation, published corpus boundary, and byte/pagination limits.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_authorized_chunks(
        self,
        workspace_id: str,
        corpus_revision_id: str,
        query: str,
        limit: int = 8,
        offset: int = 0,
    ) -> list[RetrievalChunk]:
        """Retrieve authorized abstract passages bounded strictly to the given published corpus revision."""
        # 1. Verify that corpus_revision belongs to this workspace
        rev = (
            self.db.query(CorpusRevisionModel)
            .filter_by(id=corpus_revision_id, workspace_id=workspace_id)
            .first()
        )
        if not rev:
            logger.warning(
                "Unauthorized or non-existent corpus revision '%s' for workspace '%s'",
                corpus_revision_id,
                workspace_id,
            )
            return []

        # Bound limit to max 20 to prevent runaway memory or token usage
        safe_limit = min(max(1, limit), 20)
        safe_offset = max(0, offset)

        # 2. Query corpus members, most relevant to the question first (a bounded candidate set)
        candidates = (
            self.db.query(RecordRevisionModel, SourceRecordModel)
            .join(CorpusMemberModel, CorpusMemberModel.record_revision_id == RecordRevisionModel.id)
            .join(SourceRecordModel, SourceRecordModel.id == RecordRevisionModel.source_record_id)
            .filter(CorpusMemberModel.corpus_revision_id == corpus_revision_id)
            .order_by(RecordRevisionModel.id)
            .limit(CANDIDATE_LIMIT)
            .all()
        )
        words = _query_words(query)
        ranked = sorted(
            candidates,
            key=lambda pair: -_overlap_score(words, pair[0].title, pair[0].abstract_text),
        )
        members = ranked[safe_offset : safe_offset + safe_limit]

        return [self._to_chunk(rec_rev, src_rec) for rec_rev, src_rec in members]

    @staticmethod
    def _to_chunk(rec_rev: RecordRevisionModel, src_rec: SourceRecordModel) -> RetrievalChunk:
        text = rec_rev.abstract_text or ""
        # Truncate text chunk to maximum 1500 chars for bounded model context
        bounded_text = text[:1500] if len(text) > 1500 else text
        return RetrievalChunk(
            source_record_id=src_rec.id,
            record_revision_id=rec_rev.id,
            title=rec_rev.title,
            content_hash=rec_rev.content_hash,
            text_snippet=bounded_text,
            start_cp=0,
            end_cp=len(bounded_text),
            citation_handle=f"[{src_rec.source.upper()}:{src_rec.external_id}]",
        )

    def chunk_for_target(
        self,
        workspace_id: str,
        corpus_revision_id: str,
        target_id: str,
    ) -> RetrievalChunk | None:
        """The paper a question is about: a group id (its representative) or a record revision id.

        Only a paper that belongs to this workspace's corpus revision is returned.
        """
        rev = (
            self.db.query(CorpusRevisionModel)
            .filter_by(id=corpus_revision_id, workspace_id=workspace_id)
            .first()
        )
        if not rev:
            return None
        snapshot = (
            self.db.query(GroupSnapshotModel)
            .filter_by(corpus_revision_id=corpus_revision_id, group_id=target_id)
            .first()
        )
        revision_id = snapshot.representative_revision_id if snapshot else target_id
        row = (
            self.db.query(RecordRevisionModel, SourceRecordModel)
            .join(CorpusMemberModel, CorpusMemberModel.record_revision_id == RecordRevisionModel.id)
            .join(SourceRecordModel, SourceRecordModel.id == RecordRevisionModel.source_record_id)
            .filter(
                CorpusMemberModel.corpus_revision_id == corpus_revision_id,
                RecordRevisionModel.id == revision_id,
            )
            .first()
        )
        return self._to_chunk(*row) if row else None
