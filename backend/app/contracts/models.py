"""Domain Pydantic schemas for the Evidra platform contracts."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.contracts.enums import (
    BooleanOperator,
    ConflictKind,
    CorpusRevisionState,
    CriterionVerdict,
    DecisionEventType,
    DedupEdgeStatus,
    EffectiveDecisionState,
    EligibilityStatus,
    JobKind,
    JobState,
    PicoLabel,
    RestoreMode,
    ScreeningEvidenceSource,
    SourceNamespace,
)


def utc_now() -> datetime:
    """Return current timestamp in UTC timezone."""
    return datetime.now(UTC)


class ErrorDetail(BaseModel):
    """Detailed error item for validation or domain failure."""

    model_config = ConfigDict(extra="forbid")

    field: str | None = Field(default=None, description="Affected field name if validation error")
    message: str = Field(description="Explanation of specific error")
    type: str | None = Field(default=None, description="Error classification string")


class ErrorEnvelope(BaseModel):
    """Standardized API and job error response model."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(description="Stable error code identifier (e.g. STALE_VERSION_CONFLICT, NOT_FOUND)")
    message: str = Field(description="Human-readable safe error message")
    retryable: bool = Field(default=False, description="Whether client may retry operation without modification")
    trace_id: str = Field(default_factory=lambda: str(uuid4()), description="Trace identifier for logs")
    details: list[ErrorDetail] | None = Field(default=None, description="Optional granular error details")


# ============================================================================
# Workspace Contracts
# ============================================================================

class WorkspaceCreate(BaseModel):
    """Payload to create a new review workspace."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255, description="Descriptive title of systematic review")
    description: str | None = Field(default=None, max_length=2000, description="Optional review protocol context")


class WorkspaceResponse(BaseModel):
    """Representation of an active systematic review workspace."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str = Field(description="Workspace UUID string")
    title: str = Field(description="Title of systematic review")
    description: str | None = None
    created_by: str = Field(description="Actor identifier of creator")
    created_at: datetime
    current_revision_id: str | None = Field(default=None, description="ID of latest published corpus revision")
    row_version: int = Field(default=1, description="Optimistic locking version counter")


# ============================================================================
# Criteria Contracts
# ============================================================================

class CriterionDefinition(BaseModel):
    """Definition of an individual inclusion or exclusion rule."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Criterion unique key within criteria version, e.g. 'population_adults'")
    name: str = Field(description="Display title of criterion")
    category: str = Field(description="Domain category, e.g. 'population', 'study_design', 'species'")
    is_inclusion: bool = Field(description="True if passing includes study; False if passing excludes study")
    rationale: str = Field(description="Scientific justification for criterion")
    metadata_first: bool = Field(default=True, description="Whether to check metadata tags before text heuristics")


class CriteriaVersionCreate(BaseModel):
    """Request payload to create a new immutable review criteria version."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, description="Primary systematic review question in natural language")
    pico_description: dict[str, str] = Field(
        description="PICO component definitions, e.g. {'population': 'Adults with type 2 diabetes'}"
    )
    criteria: list[CriterionDefinition] = Field(min_length=1, description="Ordered active screening rules")


class CriteriaVersionResponse(BaseModel):
    """Immutable versioned review question and screening criteria snapshot."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    workspace_id: str
    sequence: int = Field(description="Monotonic sequence number within workspace (1, 2, ...)")
    question: str
    pico_description: dict[str, str]
    criteria: list[CriterionDefinition]
    content_hash: str = Field(description="SHA-256 hash of canonical criteria JSON")
    created_at: datetime


# ============================================================================
# Query Contracts
# ============================================================================

class QueryASTNode(BaseModel):
    """Recursive node in a Boolean search query AST."""

    model_config = ConfigDict(extra="forbid")

    operator: BooleanOperator | None = Field(default=None, description="Operator if this is a branch node")
    term: str | None = Field(default=None, description="Search keyword or phrase if this is a leaf node")
    children: list[QueryASTNode] | None = Field(default=None, description="Child expressions if branch node")

    @field_validator("operator", mode="after")
    @classmethod
    def validate_node(cls, v: BooleanOperator | None, info: Any) -> BooleanOperator | None:
        # Simple structural sanity check
        return v


class QueryVersionCreate(BaseModel):
    """Payload to define an immutable search query version."""

    model_config = ConfigDict(extra="forbid")

    ast: QueryASTNode = Field(description="Root AST node representing query structure")
    start_date: str | None = Field(default=None, pattern=r"^\d{4}(-\d{2}(-\d{2})?)?$", description="YYYY, YYYY-MM, or YYYY-MM-DD")
    end_date: str | None = Field(default=None, pattern=r"^\d{4}(-\d{2}(-\d{2})?)?$", description="YYYY, YYYY-MM, or YYYY-MM-DD")
    sources: list[SourceNamespace] = Field(min_length=1, description="List of target databases")
    parent_id: str | None = Field(default=None, description="Previous query version UUID if an edit")
    criteria_version_id: str = Field(description="Associated criteria version UUID")


class QueryVersionResponse(BaseModel):
    """Immutable record of search intent and options."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    workspace_id: str
    parent_id: str | None = None
    sequence: int
    ast: QueryASTNode
    start_date: str | None = None
    end_date: str | None = None
    sources: list[SourceNamespace]
    criteria_version_id: str
    content_hash: str = Field(description="SHA-256 hash of query AST and parameters")
    created_at: datetime


class SearchExecutionCreate(BaseModel):
    """Request to execute a search query against a specific source provider."""

    model_config = ConfigDict(extra="forbid")

    source: SourceNamespace = Field(description="Target provider to query")
    synonym_expansion: bool = Field(default=False, description="Enable provider synonym expansion where available")
    cap: int | None = Field(default=None, ge=1, le=10000, description="Optional maximum hit cap to consider")


class SearchExecutionResponse(BaseModel):
    """Timestamped record of a search count acquisition from an external provider."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    query_version_id: str
    source: SourceNamespace
    exact_query: str = Field(description="Exact provider-translated query string sent to remote API")
    synonym_setting: bool
    hit_count: int = Field(ge=0, description="Total matching hits reported by provider")
    counted_at: datetime
    status: JobState
    partial: bool = Field(default=False, description="True if query or results were truncated")
    cap: int | None = None
    raw_hash: str | None = Field(default=None, description="SHA-256 checksum of raw API count response")


# ============================================================================
# Ingestion & Normalized Record Contracts
# ============================================================================

class StructuredSection(BaseModel):
    """Labeled section within a structured medical abstract (e.g. METHODS, RESULTS)."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(description="Section heading or label")
    text: str = Field(description="Section content text")


class RecordRevisionResponse(BaseModel):
    """Normalized, immutable metadata and text snapshot for an ingested literature record."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str = Field(description="Record revision UUID")
    source_record_id: str = Field(description="Parent source record identity UUID")
    source: SourceNamespace
    source_namespace: str = Field(description="Provider namespace, e.g. 'pubmed', 'pmc', 'med'")
    external_id: str = Field(description="External provider identifier, e.g. PMID '12345678'")
    content_hash: str = Field(description="SHA-256 fingerprint of normalized abstract text and title")
    title: str = Field(description="Normalized paper title")
    abstract_text: str | None = Field(default=None, description="Canonical immutable abstract text")
    structured_sections: list[StructuredSection] | None = None
    authors: list[str] = Field(default_factory=list, description="Author full or collective names")
    year: int | None = Field(default=None, ge=1800, le=2100)
    journal: str | None = None
    pages: str | None = None
    language: list[str] = Field(default_factory=list)
    publication_types: list[str] = Field(default_factory=list)
    doi: str | None = None
    pmid: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict, description="Raw unnormalized provider attributes")
    fetched_at: datetime


class ImportJobCreate(BaseModel):
    """Request to import records from approved search executions."""

    model_config = ConfigDict(extra="forbid")

    search_execution_ids: list[str] = Field(min_length=1, description="Approved search executions to fetch")
    cap: int | None = Field(default=200, ge=1, le=5000, description="Maximum total records to import")
    idempotency_key: str = Field(min_length=1, description="Client idempotency token to prevent duplicate runs")


# ============================================================================
# PICO Contracts
# ============================================================================

class PicoSpan(BaseModel):
    """Exact evidence span tagged in immutable abstract text using Unicode code points."""

    model_config = ConfigDict(extra="forbid")

    label: PicoLabel = Field(description="PICO category: P, I, C, or O")
    start_cp: int = Field(ge=0, description="Half-open zero-based start index in Unicode code points")
    end_cp: int = Field(gt=0, description="Half-open end index in Unicode code points (end_cp > start_cp)")
    quote: str = Field(min_length=1, description="Exact quoted substring matching abstract_text[start_cp:end_cp]")
    provenance: str = Field(description="Source identifier, e.g. 'rule:v1.0', 'human:reviewer_1'")

    @field_validator("end_cp")
    @classmethod
    def validate_offsets(cls, v: int, info: Any) -> int:
        start = info.data.get("start_cp")
        if start is not None and v <= start:
            raise ValueError(f"end_cp ({v}) must be strictly greater than start_cp ({start})")
        return v


class PicoResult(BaseModel):
    """Collection of exact PICO span extractions for an immutable record revision."""

    model_config = ConfigDict(extra="forbid")

    record_revision_id: str
    content_hash: str = Field(description="SHA-256 text fingerprint verified against abstract_text")
    spans: list[PicoSpan] = Field(default_factory=list)
    has_population: bool = Field(default=False)
    has_intervention: bool = Field(default=False)
    has_comparator: bool = Field(default=False, description="Explicit flag; false indicates no comparator found")
    has_outcome: bool = Field(default=False)
    method_version: str = Field(description="Extractor model/heuristic version tag")


class PicoOverrideRequest(BaseModel):
    """Reviewer manual edit or correction of PICO spans."""

    model_config = ConfigDict(extra="forbid")

    record_revision_id: str
    content_hash: str = Field(description="Must match current record revision text hash")
    expected_version: int = Field(description="Optimistic locking version counter")
    spans: list[PicoSpan] = Field(description="Complete updated list of verified PICO spans")
    reason: str | None = Field(default=None, description="Optional rationale for human correction")


# ============================================================================
# Screening & Eligibility Contracts
# ============================================================================

class CriterionEvidence(BaseModel):
    """Structured evidence evaluation for a single screening rule."""

    model_config = ConfigDict(extra="forbid")

    criterion_id: str = Field(description="Matches CriterionDefinition.id")
    name: str = Field(description="Display name of criterion")
    verdict: CriterionVerdict = Field(description="pass, fail, or unknown")
    reason_code: str = Field(description="Categorical reason code, e.g. 'ANIMAL_STUDY_EXCLUDED'")
    explanation: str = Field(description="Human-readable justification")
    evidence_snippet: str | None = Field(default=None, description="Extracted sentence or metadata evidence")
    source: ScreeningEvidenceSource = Field(description="Origin: metadata, rule, ml, llm, or human")
    method_version: str = Field(description="Version of heuristic or evaluator")


class ScreenResult(BaseModel):
    """Overall screening verdict with granular per-criterion audit trails."""

    model_config = ConfigDict(extra="forbid")

    group_id: str | None = None
    record_revision_id: str
    status: EligibilityStatus = Field(description="include, exclude, or maybe")
    reasons: list[str] = Field(default_factory=list, description="List of reason codes if excluded")
    criteria_evidence: list[CriterionEvidence] = Field(default_factory=list)
    method_version: str


class DecisionCommand(BaseModel):
    """Reviewer manual inclusion/exclusion/maybe decision."""

    model_config = ConfigDict(extra="forbid")

    status: EligibilityStatus = Field(description="Chosen eligibility status")
    reason: str | None = Field(default=None, description="Required if status is exclude")
    expected_version: int = Field(description="Current optimistic lock version of group/record")
    idempotency_key: str = Field(default_factory=lambda: str(uuid4()))


# ============================================================================
# Deduplication & Grouping Contracts
# ============================================================================

class DedupProposal(BaseModel):
    """Deterministic deduplication candidate proposal between two records."""

    model_config = ConfigDict(extra="forbid")

    record_id_a: str
    record_id_b: str
    score: float = Field(ge=0.0, le=1.0, description="Provisional similarity score")
    method_version: str
    evidence: dict[str, Any] = Field(description="Matched fields, token overlaps, author/year agreement")
    status: DedupEdgeStatus = Field(default=DedupEdgeStatus.PROPOSED)


class DedupOverrideRequest(BaseModel):
    """Reviewer confirmation or rejection of a proposed duplicate pair."""

    model_config = ConfigDict(extra="forbid")

    record_id_a: str
    record_id_b: str
    confirm: bool = Field(description="True to confirm same paper; False to reject (cannot-link constraint)")
    reason: str | None = None
    expected_version: int


class PaperGroupSummary(BaseModel):
    """Summary of a deduplicated paper group for review workbench queues."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str = Field(description="Group UUID")
    workspace_id: str
    representative_revision: RecordRevisionResponse
    member_count: int = Field(ge=1, description="Number of duplicate source records in group")
    effective_status: EffectiveDecisionState
    has_conflict: bool = Field(default=False)
    has_human_decision: bool = Field(default=False)
    last_decision_at: datetime | None = None


class PaperGroupDetail(BaseModel):
    """Detailed view of a paper group including members, machine results, and audit events."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    group: PaperGroupSummary
    members: list[RecordRevisionResponse]
    screen_result: ScreenResult | None = None
    pico_result: PicoResult | None = None
    events: list[ReviewEventResponse] = Field(default_factory=list)
    conflicts: list[ReviewConflictResponse] = Field(default_factory=list)


# ============================================================================
# Review Events & Conflicts
# ============================================================================

class ReviewEventResponse(BaseModel):
    """Append-only audit record of a human reviewer action."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    sequence: int
    workspace_id: str
    group_id: str
    event_type: DecisionEventType
    payload: dict[str, Any]
    actor_id: str
    reason: str | None = None
    supersedes_event_id: str | None = None
    created_at: datetime


class ReviewConflictResponse(BaseModel):
    """Representation of an explicit review divergence requiring human resolution."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    revision_id: str
    group_id: str
    conflicting_event_ids: list[str]
    kind: ConflictKind
    resolution_event_id: str | None = None
    created_at: datetime


class ConflictResolveRequest(BaseModel):
    """Action to resolve a group conflict."""

    model_config = ConfigDict(extra="forbid")

    chosen_status: EligibilityStatus
    reason: str = Field(min_length=1, description="Required rationale for manual conflict resolution")
    expected_version: int


# ============================================================================
# Snapshots, Diff & Jobs
# ============================================================================

class CorpusRevisionResponse(BaseModel):
    """Immutable snapshot of review state at a point in time."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    workspace_id: str
    parent_id: str | None = None
    criteria_version_id: str
    dedup_version: str
    state: CorpusRevisionState
    published_at: datetime | None = None
    decision_seq_cutoff: int | None = None
    fingerprint: str
    group_count: int = Field(default=0)
    record_count: int = Field(default=0)


class SnapshotRestoreRequest(BaseModel):
    """Request to restore a workspace to an immutable corpus revision."""

    model_config = ConfigDict(extra="forbid")

    snapshot_id: str
    mode: RestoreMode = RestoreMode.EXACT_SNAPSHOT
    expected_workspace_version: int | None = None


class CorpusDiffResponse(BaseModel):
    """Diff comparing two immutable corpus snapshots."""

    model_config = ConfigDict(extra="forbid")

    base_revision_id: str
    target_revision_id: str
    added_groups: int = 0
    removed_groups: int = 0
    merged_groups: int = 0
    split_groups: int = 0
    changed_decisions: int = 0
    conflicts_count: int = 0
    added_records: int = 0
    removed_records: int = 0
    retained_records: int = 0
    representative_changes: int = 0
    invalidation_fingerprint: str = ""
    added_record_ids: list[str] = Field(default_factory=list)
    removed_record_ids: list[str] = Field(default_factory=list)


class JobResponse(BaseModel):
    """Status and progress tracking for a background operation."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    workspace_id: str
    kind: JobKind
    request_key: str
    state: JobState
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    stage: str | None = None
    total_items: int | None = None
    processed_items: int | None = None
    error: ErrorEnvelope | None = None
    created_at: datetime
    updated_at: datetime


class ExportRequest(BaseModel):
    """Request to export confirmed included studies."""

    model_config = ConfigDict(extra="forbid")

    revision_id: str
    format: str = Field(default="csv", pattern=r"^(csv|ris)$")


class ExportResponse(BaseModel):
    """Metadata manifest of generated sanitized review export."""

    model_config = ConfigDict(extra="forbid")

    id: str
    revision_id: str
    format: str
    record_count: int
    sha256_checksum: str
    download_url: str
    created_at: datetime


# ============================================================================
# Bounded AI & RAG Assistant Schemas (Optional/Deferred Interface)
# ============================================================================

class RetrievalChunk(BaseModel):
    """Authorized textual evidence chunk retrieved from the immutable stored corpus."""

    model_config = ConfigDict(extra="forbid")

    source_record_id: str
    record_revision_id: str
    title: str
    content_hash: str
    text_snippet: str
    start_cp: int
    end_cp: int
    citation_handle: str


class AssistantRequest(BaseModel):
    """Bounded, cited query to the optional RAG assistant."""

    model_config = ConfigDict(extra="forbid")

    task: str = Field(pattern=r"^(explain_screening|suggest_query|propose_pico)$")
    target_id: str = Field(description="Target group_id or record_id within workspace")
    user_prompt: str = Field(max_length=500)


class AssistantProposal(BaseModel):
    """Structured proposal from the bounded assistant, requiring reviewer confirmation."""

    model_config = ConfigDict(extra="forbid")

    task: str
    proposal_text: str
    citations: list[RetrievalChunk] = Field(default_factory=list)
    confidence_rationale: str
    requires_human_approval: bool = True
