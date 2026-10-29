"""Domain enumeration types for Evidra systematic literature review platform."""
from enum import Enum


class SourceNamespace(str, Enum):
    """External or synthetic literature data source provider."""

    PUBMED = "pubmed"
    EUROPEPMC = "europepmc"
    SYNTHETIC = "synthetic"


class EligibilityStatus(str, Enum):
    """Screening eligibility outcome."""

    INCLUDE = "include"
    EXCLUDE = "exclude"
    MAYBE = "maybe"


class EffectiveDecisionState(str, Enum):
    """Effective decision state of a paper group or record revision."""

    INCLUDE = "include"
    EXCLUDE = "exclude"
    MAYBE = "maybe"
    CONFLICT = "conflict"
    NEEDS_REVIEW = "needs_review"
    UNSCREENED = "unscreened"


class JobState(str, Enum):
    """Lifecycle state of an asynchronous background job."""

    QUEUED = "queued"
    RUNNING = "running"
    WAITING_HUMAN = "waiting_human"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobKind(str, Enum):
    """Category of background execution."""

    SEARCH_COUNT = "search_count"
    IMPORT_RECORDS = "import_records"
    DEDUP = "dedup"
    SCREEN = "screen"
    PICO = "pico"
    EXPORT = "export"
    SNAPSHOT_RESTORE = "snapshot_restore"


class PicoLabel(str, Enum):
    """PICO evidence span annotation labels."""

    P = "P"  # Population
    I = "I"  # Intervention
    C = "C"  # Comparator
    O = "O"  # Outcome


class DecisionEventType(str, Enum):
    """Types of append-only human reviewer decision events."""

    SCREEN_DECISION = "screen_decision"
    PICO_OVERRIDE = "pico_override"
    DEDUP_OVERRIDE = "dedup_override"
    CONFLICT_RESOLUTION = "conflict_resolution"
    EVIDENCE_CORRECTION = "evidence_correction"
    DEVILS_ADVOCATE_DISPOSITION = "devils_advocate_disposition"
    MERGE_SPLIT = "merge_split"
    MERGE_REVERSAL = "merge_reversal"


class ConflictKind(str, Enum):
    """Classification of review conflicts requiring manual resolution."""

    DECISION_DIVERGENCE = "decision_divergence"
    SPLIT_AMBIGUITY = "split_ambiguity"
    METADATA_CONTRADICTION = "metadata_contradiction"


class GroupLineageOp(str, Enum):
    """Operations recorded in paper group lineage."""

    INITIAL = "initial"
    MERGE = "merge"
    SPLIT = "split"
    EXTEND = "extend"
    RETAIN = "retain"


class RestoreMode(str, Enum):
    """Restore mode for corpus snapshots."""

    EXACT_SNAPSHOT = "exact_snapshot"
    LATEST_DECISIONS = "latest_decisions"


class BooleanOperator(str, Enum):
    """Boolean AST operators for structured queries."""

    AND = "AND"
    OR = "OR"
    NOT = "NOT"


class ScreeningEvidenceSource(str, Enum):
    """Provenance origin of criterion screening evidence."""

    METADATA = "metadata"
    RULE = "rule"
    ML = "ml"
    LLM = "llm"
    HUMAN = "human"


class CriterionVerdict(str, Enum):
    """Evaluation result for an individual screening criterion."""

    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"


class CorpusRevisionState(str, Enum):
    """State of an immutable corpus snapshot."""

    BUILDING = "building"
    PUBLISHED = "published"
    FAILED = "failed"


class DedupEdgeStatus(str, Enum):
    """Status of deduplication candidate pairs."""

    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


# ============================================================================
# Evidence Passport Enums
# ============================================================================

class EvidenceClaimType(str, Enum):
    """Category of claim or study characteristic backed by an evidence passport."""

    SCREENING_RATIONALE = "screening_rationale"
    POPULATION = "population"
    INTERVENTION = "intervention"
    COMPARATOR = "comparator"
    OUTCOME = "outcome"
    STUDY_CHARACTERISTIC = "study_characteristic"


class EvidenceValidationStatus(str, Enum):
    """Deterministic structural and textual validation status of an evidence item."""

    VERIFIED = "verified"
    STALE = "stale"
    MISMATCHED = "mismatched"
    MISSING_SOURCE = "missing_source"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    NEEDS_REVIEW = "needs_review"


class EvidenceSemanticAssessment(str, Enum):
    """Semantic support evaluation assessing whether quotation logically establishes claim."""

    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    INSUFFICIENT = "insufficient"
    UNASSESSED = "unassessed"


class EvidenceProvenance(str, Enum):
    """Origin of an evidence passport item."""

    MODEL_GENERATED = "model_generated"
    DETERMINISTIC_EXTRACTION = "deterministic_extraction"
    IMPORTED_ANNOTATION = "imported_annotation"
    HUMAN_CREATED = "human_created"
    HUMAN_CORRECTED = "human_corrected"
    HUMAN_CONFIRMED = "human_confirmed"


class SearchEvolutionCategory(str, Enum):
    """Categorization of records in a search evolution comparison."""

    NEWLY_DISCOVERED = "newly_discovered"
    REPEATED = "repeated"
    MISSING_FROM_NEWER = "missing_from_newer"
    METADATA_CHANGED = "metadata_changed"
    CONFLICT = "conflict"


class RadarEvidenceStatus(str, Enum):
    """Missing-evidence radar classification for PICO information."""

    SUPPORTED = "supported"
    UNCERTAIN = "uncertain"
    NOT_FOUND = "not_found"
    CONFLICTING = "conflicting"
    STALE = "stale"
    NOT_ASSESSED = "not_assessed"


class RadarHumanReviewStatus(str, Enum):
    """Human review dimension for PICO claims."""

    UNREVIEWED = "unreviewed"
    CONFIRMED = "confirmed"
    CORRECTED = "corrected"

# ============================================================================
# Devil's Advocate Reviewer Enums
# ============================================================================

class ChallengeRecommendation(str, Enum):
    """Devil's advocate challenge recommendation outcome."""

    UPHOLD_EXCLUSION = "uphold_exclusion"
    RECONSIDER_EXCLUSION = "reconsider_exclusion"
    NEEDS_HUMAN_REVIEW = "needs_human_review"


class ChallengeDisposition(str, Enum):
    """Human reviewer disposition response to a challenge."""

    PENDING = "pending"
    CONCEDED = "conceded"
    UPHELD = "upheld"
    DISMISSED = "dismissed"


class VulnerabilityFlag(str, Enum):
    """Categorical flags explaining why an exclusion decision is vulnerable."""

    ABSTRACT_ONLY_LIMITATION = "abstract_only_limitation"
    UNCERTAIN_PICO_ELEMENT = "uncertain_pico_element"
    OVERLOOKED_SUBGROUP = "overlooked_subgroup"
    INDIRECT_COMPARATOR = "indirect_comparator"
    SURROGATE_OUTCOME = "surrogate_outcome"
    WEAK_RATIONALE = "weak_rationale"
    CRITERIA_AMBIGUITY = "criteria_ambiguity"
    COUNTER_EVIDENCE_FOUND = "counter_evidence_found"

# ============================================================================
# Duplicate Genealogy & Decision Reconciliation Enums
# ============================================================================

class DuplicateRelationshipStatus(str, Enum):
    """Status of duplicate relationship between records."""

    CONFIRMED = "confirmed"
    PROBABLE = "probable"
    POSSIBLE = "possible"
    REJECTED = "rejected"
    INVALIDATED = "invalidated"


class DuplicateConflictClassification(str, Enum):
    """Categories of decision discrepancies across duplicate records."""

    DECISION_DIVERGENCE = "decision_divergence"
    RATIONALE_DIVERGENCE = "rationale_divergence"
    AUTOMATED_VS_HUMAN = "automated_vs_human"
    MISSING_DECISION = "missing_decision"
    STALE_MERGE = "stale_merge"
    RESOLVED = "resolved"


class DuplicateMergeOperation(str, Enum):
    """Provenance operations in duplicate group lineage and history."""

    INITIAL = "initial"
    MERGE = "merge"
    SPLIT = "split"
    REVERSAL = "reversal"
    RECONCILIATION = "reconciliation"



# ============================================================================
# PRISMA 2020 Flow & Automated Reporting Enums
# ============================================================================

class PrismaStage(str, Enum):
    """PRISMA 2020 flow stages."""

    IDENTIFICATION = "identification"
    PRE_SCREENING = "pre_screening"
    SCREENING = "screening"
    RETRIEVAL = "retrieval"
    ELIGIBILITY = "eligibility"
    INCLUDED = "included"


class PrismaValidationSeverity(str, Enum):
    """Severity of PRISMA reconciliation and data integrity warnings."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class PrismaStageStatus(str, Enum):
    """Execution and availability status for PRISMA stages."""

    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"
    NOT_STARTED = "not_started"
    UNAVAILABLE = "unavailable"
