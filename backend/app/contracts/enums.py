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
