"""Bounded evidence assistant with cited retrieval and honest abstention (C06)."""
from __future__ import annotations

import logging

from app.contracts.models import (
    AssistantProposal,
    AssistantRequest,
    RetrievalChunk,
)
from app.contracts.ports import AssistantPort, EvidenceRetrievalPort
from app.gateway.messages import describe_gateway_failure
from app.gateway.protocol import (
    GatewayErrorCode,
    GatewayRequest,
    ModelGatewayProtocol,
)
from app.retrieval.index import InMemoryCorpusFTSIndex

logger = logging.getLogger(__name__)

ALLOWED_TASKS: set[str] = {
    "explain_screening",
    "suggest_query",
    "propose_pico",
}


class BoundedEvidenceAssistant(AssistantPort):
    """Bounded, cited evidence assistant implementing AssistantPort.
    
    Invariants:
    - Strictly scoped to (workspace_id, corpus_revision_id).
    - Citations must belong exclusively to authorized retrieved chunks.
    - Zero evidence -> honest abstention, never a fabricated answer.
    - At most ONE controlled query reformulation round.
    - Model outputs are proposals only (requires_human_approval=True);
      never modifies review decisions, queries, or application state.
    """

    def __init__(
        self,
        retrieval_repo: EvidenceRetrievalPort,
        gateway: ModelGatewayProtocol,
        fts_index: InMemoryCorpusFTSIndex | None = None,
        model_alias: str = "mock-research-model",
    ) -> None:
        self.retrieval_repo = retrieval_repo
        self.gateway = gateway
        self.fts_index = fts_index
        self.model_alias = model_alias

    def answer_query(
        self,
        workspace_id: str,
        corpus_revision_id: str,
        request: AssistantRequest,
    ) -> AssistantProposal:
        """Answer question with strictly cited evidence chunks or abstain."""
        # 1. Enforce allowed task boundaries
        if request.task not in ALLOWED_TASKS:
            logger.warning("Assistant: Rejected unsupported task '%s'", request.task)
            return AssistantProposal(
                task=request.task,
                proposal_text=f"Task '{request.task}' is not permitted. Allowed: {sorted(ALLOWED_TASKS)}.",
                citations=[],
                confidence_rationale="Task authorization policy rejection.",
                requires_human_approval=True,
            )

        # 2. Retrieve authorized evidence chunks
        query_text = f"{request.target_id} {request.user_prompt}".strip()
        chunks = self._retrieve_chunks(workspace_id, corpus_revision_id, query_text)
        chunks = self._with_target_first(workspace_id, corpus_revision_id, request.target_id, chunks)

        # 3. Controlled reformulation follow-up if 0 chunks found
        if not chunks:
            # Attempt 1 reformulation: search by user_prompt terms alone
            reformulated_query = request.user_prompt.strip()
            if reformulated_query and reformulated_query != query_text:
                chunks = self._retrieve_chunks(workspace_id, corpus_revision_id, reformulated_query)

        # 4. If still zero evidence -> honest abstention
        if not chunks:
            return AssistantProposal(
                task=request.task,
                proposal_text="Insufficient evidence in authorized corpus revision to formulate a proposal. Abstaining.",
                citations=[],
                confidence_rationale="Zero supporting records found within active workspace corpus revision.",
                requires_human_approval=True,
            )

        # Map authorized chunks by citation handle for verification
        chunk_map: dict[str, RetrievalChunk] = {c.citation_handle: c for c in chunks}
        # Also map by source_record_id and record_revision_id for flexible citation matching
        for c in chunks:
            chunk_map[f"[{c.source_record_id}]"] = c
            chunk_map[f"[{c.record_revision_id}]"] = c
            chunk_map[c.source_record_id] = c
            chunk_map[c.record_revision_id] = c

        # 5. Fallback if gateway is disabled or credentials missing
        if not self.gateway.is_enabled():
            first_chunk = chunks[0]
            summary_proposal = (
                f"Deterministic proposal based on authorized chunk {first_chunk.citation_handle}: "
                f"'{first_chunk.title}'. Text evidence: '{first_chunk.text_snippet[:150]}...'"
            )
            return AssistantProposal(
                task=request.task,
                proposal_text=summary_proposal,
                citations=[first_chunk],
                confidence_rationale="Rule-based deterministic extraction summary (AI disabled by policy).",
                requires_human_approval=True,
                model_error=describe_gateway_failure(GatewayErrorCode.DISABLED, None),
            )

        # 6. Invoke bounded model gateway
        evidence_payload = [
            {
                "citation_handle": c.citation_handle,
                "title": c.title,
                "snippet": c.text_snippet,
            }
            for c in chunks
        ]

        req = GatewayRequest(
            task_name="corpus_qa",
            model_alias=self.model_alias,
            prompt_context={
                "task": request.task,
                "target_id": request.target_id,
                "user_prompt": request.user_prompt,
                "evidence_chunks": evidence_payload,
                "instructions": (
                    "Formulate a factual recommendation strictly based on provided evidence_chunks. "
                    "Every assertion must include citation_handles matching the evidence. "
                    "If evidence does not support an answer, set proposal_text to 'ABSTAIN: Insufficient evidence'. "
                    'Reply with JSON only: {"proposal_text": "your answer, citing handles like [PUBMED:123]", '
                    '"cited_handles": ["[PUBMED:123]"], "confidence_rationale": "one sentence on how well the evidence supports it"}.'
                ),
            },
            # Gemini's thinking tokens count against this, so leave room for the answer itself
            max_tokens=2000,
            timeout_seconds=40.0,
        )

        resp = self.gateway.invoke(req)
        if not resp.success or not resp.data:
            # Bounded fallback on model failure
            first_chunk = chunks[0]
            return AssistantProposal(
                task=request.task,
                proposal_text=f"Deterministic fallback proposal based on {first_chunk.citation_handle}: {first_chunk.title}",
                citations=[first_chunk],
                confidence_rationale="The AI model could not answer, so this is the paper's own text; fallback used.",
                requires_human_approval=True,
                model_error=describe_gateway_failure(resp.error_code, resp.error_message),
            )

        model_output = resp.data.get("proposal_text", "")
        rationale = resp.data.get("confidence_rationale", "Synthesized from authorized corpus evidence.")

        # Check for model abstention
        if "ABSTAIN" in model_output.upper() or not model_output.strip():
            return AssistantProposal(
                task=request.task,
                proposal_text="Insufficient evidence in authorized corpus revision to formulate a proposal. Abstaining.",
                citations=[],
                confidence_rationale="Model determined evidence is insufficient.",
                requires_human_approval=True,
            )

        # 7. Validate citations: ensure every citation claimed is in chunk_map
        cited_handles = resp.data.get("cited_handles", [])
        verified_citations: list[RetrievalChunk] = []

        for h in cited_handles:
            h_str = str(h).strip()
            if h_str in chunk_map:
                chunk = chunk_map[h_str]
                if chunk not in verified_citations:
                    verified_citations.append(chunk)

        # If model did not return cited_handles explicitly, scan text for citation handles like [src-...]
        if not verified_citations:
            for handle, chunk in chunk_map.items():
                if handle in model_output and chunk not in verified_citations:
                    verified_citations.append(chunk)

        # If zero citations could be verified, abstain
        if not verified_citations:
            logger.warning("Assistant: Model response lacked verifiable citations to retrieved chunks.")
            return AssistantProposal(
                task=request.task,
                proposal_text="Unable to verify factual citations to authorized corpus. Abstaining.",
                citations=[],
                confidence_rationale="Citation verification failure: ungrounded model output.",
                requires_human_approval=True,
            )

        return AssistantProposal(
            task=request.task,
            proposal_text=model_output,
            citations=verified_citations,
            confidence_rationale=rationale,
            requires_human_approval=True,
        )

    def _with_target_first(
        self,
        workspace_id: str,
        corpus_revision_id: str,
        target_id: str,
        chunks: list[RetrievalChunk],
    ) -> list[RetrievalChunk]:
        """Put the paper the question is about first, so the answer is about it and not a neighbour."""
        find = getattr(self.retrieval_repo, "chunk_for_target", None)
        if not callable(find):
            return chunks
        target = find(workspace_id=workspace_id, corpus_revision_id=corpus_revision_id, target_id=target_id)
        if target is None:
            return chunks
        return [target, *[c for c in chunks if c.record_revision_id != target.record_revision_id]][:6]

    def _retrieve_chunks(
        self,
        workspace_id: str,
        corpus_revision_id: str,
        query: str,
    ) -> list[RetrievalChunk]:
        """Retrieve chunks from in-memory FTS index or repository."""
        # If in-memory index is provided and matches revision, use it
        if (
            self.fts_index
            and self.fts_index.workspace_id == workspace_id
            and self.fts_index.corpus_revision_id == corpus_revision_id
        ):
            return self.fts_index.search(query, limit=6)

        # Otherwise use standard repository port
        return self.retrieval_repo.get_authorized_chunks(
            workspace_id=workspace_id,
            corpus_revision_id=corpus_revision_id,
            query=query,
            limit=6,
        )
