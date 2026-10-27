"""Authorized read-only evidence retrieval repository conforming to EvidenceRetrievalPort."""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.contracts.models import RetrievalChunk
from app.contracts.ports import EvidenceRetrievalPort
from app.db.models import (
    CorpusMemberModel,
    CorpusRevisionModel,
    RecordRevisionModel,
    SourceRecordModel,
)

logger = logging.getLogger(__name__)


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

        # 2. Query corpus members
        members = (
            self.db.query(RecordRevisionModel, SourceRecordModel)
            .join(CorpusMemberModel, CorpusMemberModel.record_revision_id == RecordRevisionModel.id)
            .join(SourceRecordModel, SourceRecordModel.id == RecordRevisionModel.source_record_id)
            .filter(CorpusMemberModel.corpus_revision_id == corpus_revision_id)
            .offset(safe_offset)
            .limit(safe_limit)
            .all()
        )

        chunks: list[RetrievalChunk] = []
        for rec_rev, src_rec in members:
            text = rec_rev.abstract_text or ""
            # Truncate text chunk to maximum 1500 chars for bounded model context
            bounded_text = text[:1500] if len(text) > 1500 else text
            chunks.append(
                RetrievalChunk(
                    source_record_id=src_rec.id,
                    record_revision_id=rec_rev.id,
                    title=rec_rev.title,
                    content_hash=rec_rev.content_hash,
                    text_snippet=bounded_text,
                    start_cp=0,
                    end_cp=len(bounded_text),
                    citation_handle=f"[{src_rec.source.upper()}:{src_rec.external_id}]",
                )
            )

        return chunks
