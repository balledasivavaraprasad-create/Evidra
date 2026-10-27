"""Pure protocol ports defining interfaces between Evidra domain components."""
from typing import Any, Protocol, runtime_checkable

from app.contracts.enums import SourceNamespace
from app.contracts.models import (
    AssistantProposal,
    AssistantRequest,
    CriteriaVersionResponse,
    DedupProposal,
    PicoResult,
    QueryVersionResponse,
    RecordRevisionResponse,
    RetrievalChunk,
    ScreenResult,
    SearchExecutionResponse,
)


@runtime_checkable
class SourceAdapterPort(Protocol):
    """Port for literature database adapters (PubMed, Europe PMC)."""

    source: SourceNamespace

    def search_count(
        self,
        query: QueryVersionResponse,
        options: dict[str, Any] | None = None,
    ) -> SearchExecutionResponse:
        """Execute a count-only query against the provider API."""
        ...

    def fetch_records(
        self,
        execution: SearchExecutionResponse,
        page_size: int = 50,
        cursor: str | None = None,
    ) -> tuple[list[RecordRevisionResponse], str | None]:
        """Fetch a page of records matching the search execution, returning (records, next_cursor)."""
        ...


@runtime_checkable
class DeduplicationPort(Protocol):
    """Port for pure deduplication logic implemented by dev-B (B01)."""

    def find_candidate_pairs(
        self,
        records: list[RecordRevisionResponse],
    ) -> list[DedupProposal]:
        """Detect duplicate candidate pairs deterministically across given records."""
        ...

    def partition_groups(
        self,
        records: list[RecordRevisionResponse],
        accepted_edges: list[DedupProposal],
        cannot_link_pairs: set[tuple[str, str]],
    ) -> list[dict[str, Any]]:
        """Group records into connected components obeying cannot-link constraints."""
        ...


@runtime_checkable
class ScreeningPort(Protocol):
    """Port for deterministic screening rule evaluation implemented by dev-B (B02)."""

    def screen_record(
        self,
        record: RecordRevisionResponse,
        criteria: CriteriaVersionResponse,
    ) -> ScreenResult:
        """Evaluate inclusion/exclusion rules for a single normalized record revision."""
        ...


@runtime_checkable
class PicoPort(Protocol):
    """Port for deterministic PICO span extraction implemented by dev-C (C01)."""

    def extract_pico_spans(
        self,
        record: RecordRevisionResponse,
    ) -> PicoResult:
        """Extract exact P, I, C, O Unicode code-point spans from abstract text."""
        ...


@runtime_checkable
class EvidenceRetrievalPort(Protocol):
    """Port for authorized read-only evidence retrieval from SQLite FTS5 for RAG."""

    def get_authorized_chunks(
        self,
        workspace_id: str,
        corpus_revision_id: str,
        query: str,
        limit: int = 8,
        offset: int = 0,
    ) -> list[RetrievalChunk]:
        """Retrieve authorized text snippets bounded to a published corpus revision."""
        ...


@runtime_checkable
class LLMGatewayPort(Protocol):
    """Port for the bounded, budget-capped LLM gateway adapter (C05)."""

    def generate_structured(
        self,
        task: str,
        payload: dict[str, Any],
        schema: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate structured output under strict policy and spend budget."""
        ...


@runtime_checkable
class WorkflowPort(Protocol):
    """Port for LangGraph pipeline orchestration and human review checkpoints (C02)."""

    def trigger_pipeline(
        self,
        workspace_id: str,
        job_id: str,
    ) -> str:
        """Initiate background systematic review workflow graph."""
        ...

    def resume_human_decision(
        self,
        thread_id: str,
        event_id: str,
    ) -> None:
        """Resume an interrupted review graph after authorized human event recording."""
        ...


@runtime_checkable
class AssistantPort(Protocol):
    """Port for bounded RAG assistant queries (C06)."""

    def answer_query(
        self,
        workspace_id: str,
        corpus_revision_id: str,
        request: AssistantRequest,
    ) -> AssistantProposal:
        """Answer question with strictly cited evidence chunks."""
        ...
