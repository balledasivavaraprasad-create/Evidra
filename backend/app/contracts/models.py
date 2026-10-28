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
    EvidenceClaimType,
    EvidenceProvenance,
    EvidenceSemanticAssessment,
    EvidenceValidationStatus,
    JobKind,
    JobState,
    PicoLabel,
    RadarEvidenceStatus,
    RadarHumanReviewStatus,
    RestoreMode,
    ScreeningEvidenceSource,
    SearchEvolutionCategory,
    ChallengeDisposition,
    ChallengeRecommendation,
    DuplicateConflictClassification,
    DuplicateMergeOperation,
    DuplicateRelationshipStatus,
    SourceNamespace,
    VulnerabilityFlag,
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
    change_description: str | None = Field(default=None, description="Optional description of intent or changes for this search version")
    restored_from_version_id: str | None = Field(default=None, description="Prior query version ID if restored from an earlier search state")


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
    change_description: str | None = None
    restored_from_version_id: str | None = None
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
    evidence_bundle: EvidencePassportBundle | None = None
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


# ============================================================================
# Classical ML Screening Ranking Schemas (B05 / D06)
# ============================================================================

class RankedGroupItem(BaseModel):
    """Priority scoring item for screening workbench ordering."""

    model_config = ConfigDict(extra="forbid")

    group_id: str
    score: float = Field(ge=0.0, le=1.0, description="Priority score; higher indicates higher inclusion likelihood")
    rank: int = Field(ge=1, description="1-indexed priority rank")


class ScreeningRankRequest(BaseModel):
    """Request to compute or retrieve ML-prioritized screening order."""

    model_config = ConfigDict(extra="forbid")

    revision_id: str | None = Field(default=None, description="Corpus revision to rank; defaults to latest published")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum number of groups to return")


class ScreeningRankResponse(BaseModel):
    """Prioritized ordering recommendation for screening workbench."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    revision_id: str
    status: str
    model_version: str | None = None
    ranked_groups: list[RankedGroupItem] = Field(default_factory=list)
    reason: str | None = None


class MLRankedItem(BaseModel):
    """Prioritized literature item with continuous probability and rank."""

    model_config = ConfigDict(extra="forbid")

    record_id: str
    group_id: str | None = None
    title: str
    abstract_text: str | None = None
    score: float = Field(ge=0.0, le=1.0, description="Model priority score; higher = prioritize review")
    rank: int = Field(ge=1, description="1-indexed priority rank")
    state: str = Field(description="'SCORED', 'UNAVAILABLE', or 'OUT_OF_SCOPE'")
    reason: str | None = None
    priority_label: str = Field(default="MEDIUM", description="'HIGH', 'MEDIUM', 'LOW', or 'UNSCORED'")
    effective_status: str | None = None


class MLRankingRequest(BaseModel):
    """Request to compute or retrieve ML-prioritized queue for a corpus revision."""

    model_config = ConfigDict(extra="forbid")

    review_question: str | None = Field(default=None, description="Optional custom review question override")
    criteria_version_id: str | None = Field(default=None, description="Optional criteria version constraint")
    force_recompute: bool = Field(default=False, description="Bypass machine result cache and force recompute")
    limit: int = Field(default=100, ge=1, le=1000, description="Max items to return")
    offset: int = Field(default=0, ge=0, description="Pagination offset")


class MLRankingResponse(BaseModel):
    """Prioritized review queue response for a corpus revision."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    revision_id: str
    criteria_version_id: str | None = None
    model_version: str
    scope: str
    status: str = Field(description="'COMPLETED', 'CACHED', 'UNAVAILABLE', 'EMPTY', or 'ERROR'")
    reason: str | None = None
    total_records: int
    scored_count: int
    items: list[MLRankedItem] = Field(default_factory=list)
    computed_at: str
    duration_ms: int | None = None




# ============================================================================
# Evidence Passport Contracts
# ============================================================================

class EvidenceItemResponse(BaseModel):
    """Full auditable representation of an evidence-backed claim or PICO item."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str = Field(description="Unique evidence item UUID")
    workspace_id: str = Field(description="Associated workspace ID")
    paper_group_id: str | None = Field(default=None, description="Associated paper group ID if resolved")
    record_revision_id: str = Field(description="Immutable source record revision ID")
    claim_type: EvidenceClaimType = Field(description="Category: screening_rationale, population, etc.")
    claim_value: str = Field(description="Current claim or extracted clinical value")
    original_claim_value: str | None = Field(default=None, description="Original AI-proposed claim before human edits")
    source_field: str = Field(default="abstract", description="Source text field (e.g. abstract, title)")
    supporting_quote: str = Field(description="Exact quoted passage from source text")
    start_cp: int | None = Field(default=None, description="Zero-based start code point offset")
    end_cp: int | None = Field(default=None, description="Half-open end code point offset")
    source_fingerprint: str = Field(description="SHA-256 text fingerprint of source at extraction time")
    provenance: EvidenceProvenance = Field(description="Provenance: model_generated, deterministic, human, etc.")
    validation_status: EvidenceValidationStatus = Field(description="verified, stale, mismatched, etc.")
    validation_message: str | None = Field(default=None, description="Human-readable explanation of validation checks")
    semantic_assessment: EvidenceSemanticAssessment = Field(default=EvidenceSemanticAssessment.UNASSESSED, description="supports, contradicts, or insufficient")
    assessed_by: str | None = Field(default=None, description="Actor who performed semantic assessment")
    is_contradictory: bool = Field(default=False, description="Flag indicating passage contradicts the claim")
    uncertainty_note: str | None = Field(default=None, description="Uncertainty or limitation notes")
    reviewer_correction_reason: str | None = Field(default=None, description="Rationale recorded for human override")
    event_id: str | None = Field(default=None, description="Linked review audit event ID")
    created_at: datetime
    updated_at: datetime


class EvidencePassportSummary(BaseModel):
    """Aggregated transparency and validation metrics for a paper's evidence passport."""

    model_config = ConfigDict(extra="forbid")

    total_claims: int = Field(default=0)
    verified_quotes_count: int = Field(default=0)
    needs_review_count: int = Field(default=0)
    stale_count: int = Field(default=0)
    mismatched_count: int = Field(default=0)
    missing_source_count: int = Field(default=0)
    pico_fields_with_evidence: int = Field(default=0, description="Count of PICO categories with verified evidence")
    human_corrected_count: int = Field(default=0)
    contradictory_count: int = Field(default=0)


class EvidencePassportBundle(BaseModel):
    """Complete Evidence Passport for a literature group or paper."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    group_id: str | None = None
    record_revision_id: str
    title: str = Field(description="Paper title")
    abstract_text: str | None = Field(default=None, description="Source abstract text for UI highlighting")
    source_fingerprint: str = Field(description="Current SHA-256 fingerprint of stored source text")
    summary: EvidencePassportSummary
    items: list[EvidenceItemResponse] = Field(default_factory=list)


class EvidenceCorrectionRequest(BaseModel):
    """Reviewer manual correction of an evidence-backed claim."""

    model_config = ConfigDict(extra="forbid")

    claim_value: str = Field(min_length=1, max_length=2000, description="Corrected claim or PICO text")
    supporting_quote: str | None = Field(default=None, description="Optional updated exact quotation")
    start_cp: int | None = Field(default=None, ge=0)
    end_cp: int | None = Field(default=None, gt=0)
    semantic_assessment: EvidenceSemanticAssessment = Field(default=EvidenceSemanticAssessment.SUPPORTS)
    reason: str = Field(min_length=1, max_length=1000, description="Mandatory rationale for human correction")
    actor_id: str = Field(default="reviewer", max_length=128)


class EvidenceItemCreateRequest(BaseModel):
    """Request to create a new manual or imported evidence claim."""

    model_config = ConfigDict(extra="forbid")

    record_revision_id: str = Field(description="Target record revision ID")
    claim_type: EvidenceClaimType = Field(description="Claim category")
    claim_value: str = Field(min_length=1, max_length=2000)
    source_field: str = Field(default="abstract")
    supporting_quote: str = Field(min_length=1, description="Exact passage from source")
    start_cp: int | None = Field(default=None, ge=0)
    end_cp: int | None = Field(default=None, gt=0)
    semantic_assessment: EvidenceSemanticAssessment = Field(default=EvidenceSemanticAssessment.UNASSESSED)
    uncertainty_note: str | None = None
    actor_id: str = Field(default="reviewer", max_length=128)


class EvidenceRevalidateResponse(BaseModel):
    """Outcome of revalidating evidence claims against updated source text."""

    model_config = ConfigDict(extra="forbid")

    items_revalidated: int
    verified_count: int
    stale_count: int
    mismatched_count: int
    needs_review_count: int


class EvidenceCoverageResponse(BaseModel):
    """Review-wide transparency and evidence quality metrics."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    total_papers: int
    papers_with_verified_evidence: int
    papers_needing_review: int
    total_claims: int
    verified_claims: int
    stale_claims: int
    mismatched_claims: int
    pico_evidence_coverage_percent: float
    human_corrections_count: int


class SearchEvolutionMetadataFieldDiff(BaseModel):
    """Field-level diff between two versions of record metadata."""

    model_config = ConfigDict(extra="forbid")

    field_name: str
    base_value: str | None = None
    target_value: str | None = None


class SearchEvolutionRecordDiff(BaseModel):
    """Diff representation of a source record across search versions."""

    model_config = ConfigDict(extra="forbid")

    source_record_id: str
    external_id: str
    source: SourceNamespace
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    journal: str | None = None
    doi: str | None = None
    pmid: str | None = None
    category: SearchEvolutionCategory
    base_record_revision_id: str | None = None
    target_record_revision_id: str | None = None
    field_diffs: list[SearchEvolutionMetadataFieldDiff] = Field(default_factory=list)
    screening_decision: EffectiveDecisionState | None = None
    screening_reason: str | None = None
    screening_preserved_from_version_id: str | None = None
    metadata_changed_since_screening: bool = False


class SearchEvolutionDiffSummary(BaseModel):
    """Aggregated counts and metrics comparing two search versions."""

    model_config = ConfigDict(extra="forbid")

    base_version_id: str
    base_sequence: int
    target_version_id: str
    target_sequence: int
    total_base_records: int
    total_target_records: int
    newly_discovered_count: int
    repeated_count: int
    missing_from_newer_count: int
    metadata_changed_count: int
    conflicts_count: int
    screened_target_count: int
    unscreened_target_count: int


class SearchEvolutionDiffResponse(BaseModel):
    """Detailed diff comparing two search versions across all records."""

    model_config = ConfigDict(extra="forbid")

    summary: SearchEvolutionDiffSummary
    records: list[SearchEvolutionRecordDiff]


class SearchEvolutionVersionSummary(BaseModel):
    """Timeline summary of a query version and its executed search runs."""

    model_config = ConfigDict(extra="forbid")

    id: str
    sequence: int
    workspace_id: str
    parent_id: str | None = None
    restored_from_version_id: str | None = None
    change_description: str | None = None
    created_at: datetime
    sources: list[SourceNamespace]
    start_date: str | None = None
    end_date: str | None = None
    total_records: int
    screened_records: int
    unscreened_records: int
    new_records_count: int = 0
    repeated_records_count: int = 0
    executions: list[SearchExecutionResponse] = Field(default_factory=list)


class SearchRestoreRequest(BaseModel):
    """Request payload to safely restore a prior search configuration."""

    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, description="Optional reason for restoring this search version")
    actor_id: str = Field(default="researcher", max_length=128)


class SearchRestoreResponse(BaseModel):
    """Response after restoring an earlier search version."""

    model_config = ConfigDict(extra="forbid")

    restored_query: QueryVersionResponse
    restored_from_version_id: str
    message: str


class RadarFieldDetail(BaseModel):
    """Detailed PICO element evidence status and supporting passage."""

    model_config = ConfigDict(extra="forbid")

    claim_type: EvidenceClaimType
    field_label: str
    radar_status: RadarEvidenceStatus
    human_review_status: RadarHumanReviewStatus
    claim_value: str | None = None
    original_claim_value: str | None = None
    source_field: str = Field(default="abstract", description="Examined source text container (e.g. abstract)")
    supporting_quote: str | None = None
    start_cp: int | None = None
    end_cp: int | None = None
    validation_status: EvidenceValidationStatus = Field(default=EvidenceValidationStatus.NEEDS_REVIEW)
    validation_message: str | None = None
    semantic_assessment: EvidenceSemanticAssessment = Field(default=EvidenceSemanticAssessment.UNASSESSED)
    is_contradictory: bool = False
    uncertainty_note: str | None = None
    reviewer_correction_reason: str | None = None
    reviewer_notes: str | None = None
    evidence_id: str | None = None
    updated_at: datetime | None = None


class ArticleRadarResponse(BaseModel):
    """Article-level Missing-Evidence Radar representing all 4 PICO dimensions."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    group_id: str
    paper_title: str
    source_text: str | None = None
    source_field: str = Field(default="abstract")
    has_source_text: bool = True
    effective_decision: EffectiveDecisionState
    screening_reason: str | None = None
    pico: dict[str, RadarFieldDetail]
    overall_coverage_pct: float
    needs_human_review: bool


class ReviewRadarDimensionSummary(BaseModel):
    """Aggregated coverage metrics for one PICO dimension across review."""

    model_config = ConfigDict(extra="forbid")

    dimension: EvidenceClaimType
    total_assessed: int
    supported_count: int
    uncertain_count: int
    not_found_count: int
    conflicting_count: int
    stale_count: int
    not_assessed_count: int
    human_confirmed_count: int
    human_corrected_count: int
    pending_review_count: int
    supported_percent: float


class ReviewRadarArticleRow(BaseModel):
    """Single article row in review-level coverage matrix."""

    model_config = ConfigDict(extra="forbid")

    group_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    journal: str | None = None
    doi: str | None = None
    pmid: str | None = None
    has_source_text: bool = True
    effective_decision: EffectiveDecisionState
    population_status: RadarEvidenceStatus
    intervention_status: RadarEvidenceStatus
    comparator_status: RadarEvidenceStatus
    outcome_status: RadarEvidenceStatus
    population_value: str | None = None
    intervention_value: str | None = None
    comparator_value: str | None = None
    outcome_value: str | None = None
    needs_review: bool = False
    priority_rank: int = 0


class ReviewRadarResponse(BaseModel):
    """Review-wide Missing-Evidence Radar matrix and dimension statistics."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    total_articles: int
    articles_with_source_text: int
    articles_without_source_text: int
    dimension_summaries: dict[str, ReviewRadarDimensionSummary]
    total_fields_supported_percent: float
    needs_review_total: int
    rows: list[ReviewRadarArticleRow]


class RadarConfirmRequest(BaseModel):
    """Payload to confirm an extracted PICO value as verified."""

    model_config = ConfigDict(extra="forbid")

    actor_id: str = Field(default="reviewer", max_length=128)
    notes: str | None = Field(default=None, max_length=1000)


class RadarCorrectRequest(BaseModel):
    """Payload to correct a PICO value with reviewer rationale."""

    model_config = ConfigDict(extra="forbid")

    claim_value: str = Field(min_length=1, max_length=2000)
    supporting_quote: str | None = None
    start_cp: int | None = None
    end_cp: int | None = None
    reason: str = Field(min_length=1, max_length=1000, description="Mandatory rationale for human correction")
    actor_id: str = Field(default="reviewer", max_length=128)


class RadarFlagUncertainRequest(BaseModel):
    """Payload to flag a PICO element as ambiguous or uncertain."""

    model_config = ConfigDict(extra="forbid")

    uncertainty_note: str = Field(min_length=1, max_length=1000)
    actor_id: str = Field(default="reviewer", max_length=128)


class RadarFlagConflictRequest(BaseModel):
    """Payload to flag conflicting evidence for a PICO element."""

    model_config = ConfigDict(extra="forbid")

    conflict_explanation: str = Field(min_length=1, max_length=1000)
    competing_quote: str | None = None
    actor_id: str = Field(default="reviewer", max_length=128)

# ============================================================================
# Devil's Advocate Reviewer Models
# ============================================================================

class CounterArgumentItem(BaseModel):
    """Structured counter-argument supporting potential eligibility."""

    model_config = ConfigDict(extra="forbid")

    argument: str = Field(description="Summary of why paper might be eligible")
    supporting_quote: str = Field(description="Verbatim quote from source text supporting counter-argument")
    source_field: str = Field(default="abstract", description="Field where quote was located")
    relevance_aspect: str = Field(description="PICO or study design aspect supported by quote")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class DevilsAdvocateChallengeResponse(BaseModel):
    """Devil's Advocate challenge assessment for a proposed exclusion."""

    model_config = ConfigDict(extra="forbid")

    id: str
    workspace_id: str
    group_id: str
    record_revision_id: str
    proposed_decision: str
    original_exclusion_reason: str | None = None
    recommendation: ChallengeRecommendation
    vulnerability_score: float = Field(ge=0.0, le=1.0, description="Fragility score where 1.0 is extremely vulnerable/likely false exclusion")
    critique: str = Field(description="Detailed challenge rationale")
    counter_arguments: list[CounterArgumentItem] = Field(default_factory=list)
    vulnerability_flags: list[VulnerabilityFlag] = Field(default_factory=list)
    disposition: ChallengeDisposition = Field(default=ChallengeDisposition.PENDING)
    disposition_notes: str | None = None
    disposition_by: str | None = None
    disposed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class DevilsAdvocateDispositionRequest(BaseModel):
    """Payload for human reviewer disposition on a Devil's Advocate challenge."""

    model_config = ConfigDict(extra="forbid")

    disposition: ChallengeDisposition = Field(description="Human decision: conceded, upheld, or dismissed")
    notes: str | None = Field(default=None, max_length=2000, description="Reviewer notes or justification")
    actor_id: str = Field(default="reviewer", max_length=128)
    conceded_decision: EligibilityStatus | None = Field(
        default=None,
        description="New eligibility status if conceded (e.g. include or maybe)",
    )


class DevilsAdvocateGenerateRequest(BaseModel):
    """Payload to request or force a fresh Devil's Advocate challenge."""

    model_config = ConfigDict(extra="forbid")

    proposed_decision: str | None = Field(default=None, description="Proposed decision (defaults to group effective decision)")
    exclusion_reason: str | None = Field(default=None, description="Explicit exclusion reason to challenge")
    force_refresh: bool = Field(default=False, description="Re-run challenge generation even if existing challenge is present")


class DevilsAdvocateDashboardItem(BaseModel):
    """Summary item for review-level Devil's Advocate dashboard."""

    model_config = ConfigDict(extra="forbid")

    challenge_id: str
    group_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    pmid: str | None = None
    doi: str | None = None
    proposed_decision: str
    original_exclusion_reason: str | None = None
    recommendation: ChallengeRecommendation
    vulnerability_score: float
    vulnerability_flags: list[VulnerabilityFlag] = Field(default_factory=list)
    disposition: ChallengeDisposition
    counter_argument_count: int
    created_at: datetime


class DevilsAdvocateDashboardResponse(BaseModel):
    """Review-level Devil's Advocate metrics and challenge ledger."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    total_challenged: int
    pending_challenges: int
    high_vulnerability_count: int
    conceded_count: int
    upheld_count: int
    dismissed_count: int
    concession_rate: float = Field(description="Percentage of resolved challenges that were conceded")
    false_exclusions_prevented: int = Field(description="Exclusions successfully reversed to Include or Maybe")
    challenges: list[DevilsAdvocateDashboardItem] = Field(default_factory=list)

# ============================================================================
# Duplicate Genealogy & Decision Reconciliation Models
# ============================================================================

class FieldProvenanceItem(BaseModel):
    """Field-level metadata provenance comparison across duplicate records."""

    model_config = ConfigDict(extra="forbid")

    field_name: str = Field(description="Name of metadata field (e.g. title, doi, authors, year, journal)")
    canonical_value: str | None = Field(default=None, description="Selected canonical value for group")
    canonical_source: str = Field(description="Source database providing canonical value")
    source_record_id: str = Field(description="ID of source record supplying canonical value")
    alternatives: list[dict[str, Any]] = Field(default_factory=list, description="Alternative values from other duplicates")
    has_discrepancy: bool = Field(default=False, description="True if alternative values differ non-trivially")


class DuplicateRecordMemberDetail(BaseModel):
    """Detail of an individual source record within a duplicate group."""

    model_config = ConfigDict(extra="forbid")

    source_record_id: str
    record_revision_id: str
    external_id: str
    source_namespace: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    doi: str | None = None
    pmid: str | None = None
    journal: str | None = None
    abstract_text: str | None = None
    is_canonical: bool = False
    individual_decision: str = "unscreened"
    decision_source: str = "none"
    decision_rationale: str | None = None
    decision_by: str | None = None
    decision_at: datetime | None = None


class DuplicateMatchSignalDetail(BaseModel):
    """Actual deterministic evidence and similarity score linking a candidate pair."""

    model_config = ConfigDict(extra="forbid")

    record_id_a: str
    record_id_b: str
    score: float
    status: DuplicateRelationshipStatus
    signals: list[str] = Field(default_factory=list)
    evidence_detail: dict[str, Any] = Field(default_factory=dict)


class DecisionConflictDetail(BaseModel):
    """Detailed discrepancy between decisions on linked duplicate records."""

    model_config = ConfigDict(extra="forbid")

    conflict_id: str | None = None
    classification: DuplicateConflictClassification
    affected_records: list[str] = Field(default_factory=list)
    competing_decisions: list[dict[str, Any]] = Field(default_factory=list)
    explanation: str
    is_resolved: bool = False
    resolution: str | None = None
    resolved_by: str | None = None
    resolved_at: datetime | None = None


class DuplicateMergeHistoryItem(BaseModel):
    """Audited merge, split, or reversal event in group genealogy."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    operation: DuplicateMergeOperation
    affected_source_ids: list[str] = Field(default_factory=list)
    canonical_record_id: str | None = None
    actor_id: str
    reason: str | None = None
    timestamp: datetime
    can_reverse: bool = True
    reversal_blockers: list[str] = Field(default_factory=list)
    is_reversed: bool = False


class DuplicateGroupGenealogyResponse(BaseModel):
    """Full genealogy, matching signals, conflicts, and provenance for a duplicate group."""

    model_config = ConfigDict(extra="forbid")

    group_id: str
    workspace_id: str
    canonical_record_id: str
    membership_fingerprint: str
    row_version: int
    effective_decision: str
    members: list[DuplicateRecordMemberDetail] = Field(default_factory=list)
    pairwise_signals: list[DuplicateMatchSignalDetail] = Field(default_factory=list)
    active_conflicts: list[DecisionConflictDetail] = Field(default_factory=list)
    field_provenance: list[FieldProvenanceItem] = Field(default_factory=list)
    merge_history: list[DuplicateMergeHistoryItem] = Field(default_factory=list)


class DuplicateReconcileRequest(BaseModel):
    """Payload to reconcile a conflicting decision across duplicate records."""

    model_config = ConfigDict(extra="forbid")

    chosen_decision: EligibilityStatus
    reason: str = Field(min_length=1, max_length=1000, description="Mandatory clinical/methodological rationale for reconciliation")
    actor_id: str = Field(default="reviewer", max_length=128)
    apply_to_all_members: bool = Field(default=True, description="Propagate reconciled decision to all group members")
    expected_version: int = Field(description="Group row version for optimistic concurrency check")


class DuplicateSplitRequest(BaseModel):
    """Payload to safely split a record out of a duplicate group."""

    model_config = ConfigDict(extra="forbid")

    source_record_ids_to_split: list[str] = Field(min_length=1, description="List of source record IDs to separate into independent group")
    reason: str = Field(min_length=1, max_length=1000, description="Mandatory justification for splitting duplicate group")
    actor_id: str = Field(default="reviewer", max_length=128)
    mark_as_cannot_link: bool = Field(default=True, description="Enforce permanent cannot-link constraint on pairwise edges")
    expected_version: int = Field(description="Group row version for optimistic concurrency check")


class DuplicateReverseMergeRequest(BaseModel):
    """Payload to reverse an earlier merge operation without erasing audit history."""

    model_config = ConfigDict(extra="forbid")

    merge_event_id: str = Field(description="ID of merge event to reverse")
    reason: str = Field(min_length=1, max_length=1000, description="Rationale for merge reversal")
    actor_id: str = Field(default="reviewer", max_length=128)
    expected_version: int = Field(description="Group row version for optimistic concurrency check")


class DuplicateWorkspaceSummaryItem(BaseModel):
    """Summary item of duplicate group for workspace overview."""

    model_config = ConfigDict(extra="forbid")

    group_id: str
    canonical_title: str
    member_count: int
    sources: list[str] = Field(default_factory=list)
    effective_decision: str
    has_unresolved_conflict: bool
    conflict_types: list[str] = Field(default_factory=list)
    confidence_label: str
    created_at: datetime


class DuplicateWorkspaceSummaryResponse(BaseModel):
    """Workspace-wide overview of duplicate groups, conflicts, and reconciliation status."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    total_duplicate_groups: int
    total_duplicate_records: int
    groups_with_conflicts: int
    resolved_conflicts_count: int
    pending_candidate_pairs: int
    groups: list[DuplicateWorkspaceSummaryItem] = Field(default_factory=list)

