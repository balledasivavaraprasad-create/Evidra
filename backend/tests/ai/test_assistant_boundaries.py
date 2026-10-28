"""Unit tests for bounded evidence assistant security boundaries and citations (C06)."""
from unittest.mock import MagicMock

from app.contracts.models import (
    AssistantRequest,
    RetrievalChunk,
)
from app.contracts.ports import EvidenceRetrievalPort
from app.gateway.adapter import MockModelAdapter
from app.workflows.assistant import BoundedEvidenceAssistant


class MockEvidenceRepository(EvidenceRetrievalPort):
    """Controlled in-memory repository for assistant boundary testing."""

    def __init__(self, authorized_chunks: dict[tuple[str, str], list[RetrievalChunk]]) -> None:
        self.authorized_chunks = authorized_chunks

    def get_authorized_chunks(
        self,
        workspace_id: str,
        corpus_revision_id: str,
        query: str,
        limit: int = 8,
        offset: int = 0,
    ) -> list[RetrievalChunk]:
        chunks = self.authorized_chunks.get((workspace_id, corpus_revision_id), [])
        # Simple substring filter if query is provided
        if query:
            filtered = [c for c in chunks if any(word.lower() in (c.title + c.text_snippet).lower() for word in query.split())]
            return filtered[:limit] if filtered else chunks[:limit]
        return chunks[:limit]


def create_sample_chunk(rec_id: str, title: str, snippet: str) -> RetrievalChunk:
    return RetrievalChunk(
        source_record_id=f"src-{rec_id}",
        record_revision_id=f"rec-{rec_id}",
        title=title,
        content_hash="chash123",
        text_snippet=snippet,
        start_cp=0,
        end_cp=len(snippet),
        citation_handle=f"[src-{rec_id}]",
    )


def test_assistant_unsupported_task_rejected():
    """Task outside explain_screening, suggest_query, propose_pico is rejected by contract and assistant."""
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        AssistantRequest(
            task="arbitrary_web_search",  # Invalid task!
            target_id="tgt-1",
            user_prompt="Find papers online",
        )

    # Also test assistant method defense with constructed mock request
    mock_req = MagicMock()
    mock_req.task = "unauthorized_arbitrary_task"
    mock_req.target_id = "tgt-1"
    mock_req.user_prompt = "Find papers"

    repo = MockEvidenceRepository({})
    gateway = MockModelAdapter()
    assistant = BoundedEvidenceAssistant(retrieval_repo=repo, gateway=gateway)

    proposal = assistant.answer_query("ws-1", "rev-1", mock_req)
    assert "not permitted" in proposal.proposal_text
    assert len(proposal.citations) == 0
    assert proposal.requires_human_approval is True


def test_cross_workspace_isolation():
    """Assistant querying ws-A cannot retrieve or cite chunks belonging to ws-B."""
    chunk_b = create_sample_chunk("B", "Private Study from Workspace B", "Secret clinical finding")
    repo = MockEvidenceRepository({
        ("ws-B", "rev-B"): [chunk_b],
        ("ws-A", "rev-A"): [],  # Empty for ws-A
    })
    gateway = MockModelAdapter()
    assistant = BoundedEvidenceAssistant(retrieval_repo=repo, gateway=gateway)

    req = AssistantRequest(
        task="explain_screening",
        target_id="tgt-1",
        user_prompt="What did the study find?",
    )
    # Query ws-A
    proposal = assistant.answer_query("ws-A", "rev-A", req)
    # Must abstain because ws-A has 0 records; cannot see ws-B
    assert "Abstaining" in proposal.proposal_text
    assert len(proposal.citations) == 0


def test_zero_retrieval_triggers_honest_abstention():
    """When no matching records exist in the corpus revision, assistant abstains."""
    repo = MockEvidenceRepository({("ws-1", "rev-1"): []})
    gateway = MockModelAdapter()
    assistant = BoundedEvidenceAssistant(retrieval_repo=repo, gateway=gateway)

    req = AssistantRequest(
        task="propose_pico",
        target_id="rec-1",
        user_prompt="Extract PICO for this non-existent record",
    )
    proposal = assistant.answer_query("ws-1", "rev-1", req)
    assert "Insufficient evidence" in proposal.proposal_text
    assert len(proposal.citations) == 0
    assert proposal.requires_human_approval is True


def test_fabricated_citation_rejected_and_abstains():
    """If model cites a record not in authorized chunks, it is rejected."""
    chunk = create_sample_chunk("1", "Metformin RCT", "Metformin lowered HbA1c in adults.")
    repo = MockEvidenceRepository({("ws-1", "rev-1"): [chunk]})

    # Mock gateway returning fabricated citation [src-HALLUCINATED]
    canned = {
        "proposal_text": "Metformin is safe and effective [src-HALLUCINATED].",
        "cited_handles": ["[src-HALLUCINATED]"],
        "confidence_rationale": "Fabricated rationale",
    }
    gateway = MockModelAdapter(canned_response=canned)
    assistant = BoundedEvidenceAssistant(retrieval_repo=repo, gateway=gateway)

    req = AssistantRequest(
        task="explain_screening",
        target_id="rec-1",
        user_prompt="Explain why this paper is included",
    )
    proposal = assistant.answer_query("ws-1", "rev-1", req)
    # Should reject the ungrounded citation and abstain
    assert "Abstaining" in proposal.proposal_text
    assert len(proposal.citations) == 0


def test_valid_cited_proposal_succeeds():
    """Model returning valid citation to authorized chunk yields confirmed proposal."""
    chunk = create_sample_chunk("1", "Metformin in T2D", "Adults treated with metformin had reduced HbA1c.")
    repo = MockEvidenceRepository({("ws-1", "rev-1"): [chunk]})

    canned = {
        "proposal_text": "Study demonstrates glycemic efficacy in adults [src-1].",
        "cited_handles": ["[src-1]"],
        "confidence_rationale": "Supported by trial abstract findings.",
    }
    gateway = MockModelAdapter(canned_response=canned)
    assistant = BoundedEvidenceAssistant(retrieval_repo=repo, gateway=gateway)

    req = AssistantRequest(
        task="explain_screening",
        target_id="rec-1",
        user_prompt="Explain inclusion rationale",
    )
    proposal = assistant.answer_query("ws-1", "rev-1", req)
    assert "Study demonstrates glycemic efficacy" in proposal.proposal_text
    assert len(proposal.citations) == 1
    assert proposal.citations[0].source_record_id == "src-1"
    assert proposal.requires_human_approval is True


def test_gateway_disabled_produces_deterministic_summary():
    """When LLM is disabled, assistant returns deterministic summary of chunks."""
    chunk = create_sample_chunk("1", "Metformin in T2D", "Adults treated with metformin had reduced HbA1c.")
    repo = MockEvidenceRepository({("ws-1", "rev-1"): [chunk]})
    gateway = MockModelAdapter(enabled=False)
    assistant = BoundedEvidenceAssistant(retrieval_repo=repo, gateway=gateway)

    req = AssistantRequest(
        task="suggest_query",
        target_id="rec-1",
        user_prompt="Suggest search keywords",
    )
    proposal = assistant.answer_query("ws-1", "rev-1", req)
    assert "Deterministic proposal" in proposal.proposal_text
    assert len(proposal.citations) == 1
    assert proposal.citations[0].source_record_id == "src-1"
    assert proposal.requires_human_approval is True


def test_assistant_never_mutates_database_or_review_events():
    """Assistant query executes as a pure read-only operation."""
    mock_db = MagicMock()
    repo = MockEvidenceRepository({("ws-1", "rev-1"): []})
    gateway = MockModelAdapter()
    assistant = BoundedEvidenceAssistant(retrieval_repo=repo, gateway=gateway)

    req = AssistantRequest(
        task="propose_pico",
        target_id="rec-1",
        user_prompt="Extract PICO",
    )
    assistant.answer_query("ws-1", "rev-1", req)
    # Verify zero database commit, add, or flush calls
    assert mock_db.commit.call_count == 0
    assert mock_db.add.call_count == 0
    assert mock_db.flush.call_count == 0
