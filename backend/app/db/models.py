"""SQLAlchemy ORM models defining the Evidra foundation database schema."""
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


def utc_now() -> datetime:
    """Return current timestamp in UTC timezone."""
    return datetime.now(UTC)


def generate_uuid() -> str:
    """Generate string UUID4."""
    return str(uuid4())


class WorkspaceModel(Base):
    """Systematic review workspace."""

    __tablename__ = "workspaces"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_by = Column(String(128), nullable=False)
    current_revision_id = Column(String(64), nullable=True)
    row_version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    criteria_versions = relationship("CriteriaVersionModel", back_populates="workspace", cascade="all, delete-orphan")
    query_versions = relationship("QueryVersionModel", back_populates="workspace", cascade="all, delete-orphan")
    source_records = relationship("SourceRecordModel", back_populates="workspace", cascade="all, delete-orphan")
    jobs = relationship("JobModel", back_populates="workspace", cascade="all, delete-orphan")
    corpus_revisions = relationship("CorpusRevisionModel", back_populates="workspace", cascade="all, delete-orphan")
    paper_groups = relationship("PaperGroupModel", back_populates="workspace", cascade="all, delete-orphan")
    review_events = relationship("ReviewEventModel", back_populates="workspace", cascade="all, delete-orphan")
    evidence_passports = relationship("EvidencePassportModel", back_populates="workspace", cascade="all, delete-orphan")
    devils_advocate_challenges = relationship("DevilsAdvocateChallengeModel", backref="workspace", cascade="all, delete-orphan")
    duplicate_merge_events = relationship("DuplicateMergeEventModel", backref="workspace", cascade="all, delete-orphan")


class CriteriaVersionModel(Base):
    """Immutable snapshot of question and criteria version."""

    __tablename__ = "criteria_versions"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    question = Column(Text, nullable=False)
    pico_json = Column(Text, nullable=False)
    criteria_json = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    workspace = relationship("WorkspaceModel", back_populates="criteria_versions")
    query_versions = relationship("QueryVersionModel", back_populates="criteria_version")

    __table_args__ = (
        UniqueConstraint("workspace_id", "sequence", name="uq_criteria_workspace_sequence"),
    )


class QueryVersionModel(Base):
    """Immutable search query specification."""

    __tablename__ = "query_versions"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(String(64), ForeignKey("query_versions.id"), nullable=True)
    sequence = Column(Integer, nullable=False)
    ast_json = Column(Text, nullable=False)
    start_date = Column(String(32), nullable=True)
    end_date = Column(String(32), nullable=True)
    sources_json = Column(Text, nullable=False)
    criteria_version_id = Column(String(64), ForeignKey("criteria_versions.id"), nullable=False)
    content_hash = Column(String(64), nullable=False)
    change_description = Column(Text, nullable=True)
    restored_from_version_id = Column(String(64), ForeignKey("query_versions.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    workspace = relationship("WorkspaceModel", back_populates="query_versions")
    criteria_version = relationship("CriteriaVersionModel", back_populates="query_versions")
    search_executions = relationship("SearchExecutionModel", back_populates="query_version", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("workspace_id", "sequence", name="uq_query_workspace_sequence"),
    )


class SearchExecutionModel(Base):
    """Execution of a query version against an external literature provider."""

    __tablename__ = "search_executions"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    query_version_id = Column(String(64), ForeignKey("query_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    source = Column(String(32), nullable=False)
    exact_query = Column(Text, nullable=False)
    synonym_setting = Column(Boolean, default=False, nullable=False)
    hit_count = Column(Integer, nullable=False)
    counted_at = Column(DateTime, default=utc_now, nullable=False)
    status = Column(String(32), nullable=False)
    partial = Column(Boolean, default=False, nullable=False)
    cap = Column(Integer, nullable=True)
    raw_hash = Column(String(64), nullable=True)

    query_version = relationship("QueryVersionModel", back_populates="search_executions")
    memberships = relationship("QueryMembershipModel", back_populates="search_execution", cascade="all, delete-orphan")


class SourceRecordModel(Base):
    """Canonical source identity (one record found per external provider ID)."""

    __tablename__ = "source_records"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    source = Column(String(32), nullable=False)
    source_namespace = Column(String(64), nullable=False)
    external_id = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    workspace = relationship("WorkspaceModel", back_populates="source_records")
    revisions = relationship("RecordRevisionModel", back_populates="source_record", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("workspace_id", "source", "source_namespace", "external_id", name="uq_source_records_identity"),
    )


class RecordRevisionModel(Base):
    """Immutable normalized metadata and text revision for a source record."""

    __tablename__ = "record_revisions"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    source_record_id = Column(String(64), ForeignKey("source_records.id", ondelete="CASCADE"), nullable=False, index=True)
    content_hash = Column(String(64), nullable=False)
    title = Column(Text, nullable=False)
    abstract_text = Column(Text, nullable=True)
    structured_sections_json = Column(Text, nullable=True)
    authors_json = Column(Text, nullable=True)
    year = Column(Integer, nullable=True)
    journal = Column(String(512), nullable=True)
    pages = Column(String(128), nullable=True)
    language_json = Column(Text, nullable=True)
    publication_types_json = Column(Text, nullable=True)
    doi = Column(String(256), nullable=True, index=True)
    pmid = Column(String(64), nullable=True, index=True)
    metadata_json = Column(Text, nullable=True)
    fetched_at = Column(DateTime, default=utc_now, nullable=False)

    source_record = relationship("SourceRecordModel", back_populates="revisions")

    __table_args__ = (
        UniqueConstraint("source_record_id", "content_hash", name="uq_record_revisions_content"),
    )


class QueryMembershipModel(Base):
    """Associates a search execution with imported source records and revisions."""

    __tablename__ = "query_memberships"

    search_execution_id = Column(String(64), ForeignKey("search_executions.id", ondelete="CASCADE"), nullable=False)
    source_record_id = Column(String(64), ForeignKey("source_records.id", ondelete="CASCADE"), nullable=False)
    record_revision_id = Column(String(64), ForeignKey("record_revisions.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    search_execution = relationship("SearchExecutionModel", back_populates="memberships")

    __table_args__ = (
        PrimaryKeyConstraint("search_execution_id", "source_record_id", name="pk_query_memberships"),
    )


class JobModel(Base):
    """Background operation tracking and durable lease state."""

    __tablename__ = "jobs"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String(64), nullable=False)
    request_key = Column(String(128), nullable=False)
    payload_hash = Column(String(64), nullable=False)
    state = Column(String(32), nullable=False)
    progress = Column(Float, default=0.0, nullable=False)
    stage = Column(String(64), nullable=True)
    total_items = Column(Integer, nullable=True)
    processed_items = Column(Integer, nullable=True)
    error_json = Column(Text, nullable=True)
    lease_owner = Column(String(128), nullable=True)
    lease_until = Column(DateTime, nullable=True)
    attempt = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    workspace = relationship("WorkspaceModel", back_populates="jobs")

    __table_args__ = (
        UniqueConstraint("workspace_id", "request_key", name="uq_jobs_request_key"),
    )


class RunLogModel(Base):
    """Append-only execution step log for jobs."""

    __tablename__ = "runs"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(String(64), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    stage = Column(String(64), nullable=False)
    attempt = Column(Integer, default=1, nullable=False)
    input_hash = Column(String(64), nullable=True)
    output_hash = Column(String(64), nullable=True)
    status = Column(String(32), nullable=False)
    error_code = Column(String(64), nullable=True)
    trace_id = Column(String(64), nullable=False)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)


class IdempotencyRecordModel(Base):
    """Atomic records for client idempotency keys."""

    __tablename__ = "idempotency_keys"

    key = Column(String(128), primary_key=True)
    workspace_id = Column(String(64), nullable=False, index=True)
    endpoint = Column(String(128), nullable=False)
    request_hash = Column(String(64), nullable=False)
    response_code = Column(Integer, nullable=False)
    response_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)


class CorpusRevisionModel(Base):
    """Immutable snapshot of literature corpus state."""

    __tablename__ = "corpus_revisions"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(String(64), ForeignKey("corpus_revisions.id"), nullable=True)
    criteria_version_id = Column(String(64), ForeignKey("criteria_versions.id"), nullable=False)
    dedup_version = Column(String(32), nullable=False)
    state = Column(String(32), nullable=False)
    published_at = Column(DateTime, nullable=True)
    decision_seq_cutoff = Column(Integer, nullable=True)
    fingerprint = Column(String(64), nullable=False)
    group_count = Column(Integer, default=0, nullable=False)
    record_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    workspace = relationship("WorkspaceModel", back_populates="corpus_revisions")


class CorpusQueryModel(Base):
    """Search executions included in a corpus revision."""

    __tablename__ = "corpus_queries"

    corpus_revision_id = Column(String(64), ForeignKey("corpus_revisions.id", ondelete="CASCADE"), nullable=False)
    search_execution_id = Column(String(64), ForeignKey("search_executions.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("corpus_revision_id", "search_execution_id", name="pk_corpus_queries"),
    )


class CorpusMemberModel(Base):
    """Record revisions included in a corpus revision snapshot."""

    __tablename__ = "corpus_members"

    corpus_revision_id = Column(String(64), ForeignKey("corpus_revisions.id", ondelete="CASCADE"), nullable=False)
    source_record_id = Column(String(64), ForeignKey("source_records.id", ondelete="CASCADE"), nullable=False)
    record_revision_id = Column(String(64), ForeignKey("record_revisions.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("corpus_revision_id", "source_record_id", name="pk_corpus_members"),
    )


class PaperGroupModel(Base):
    """Deduplicated paper group identity. ID is never recycled."""

    __tablename__ = "paper_groups"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    membership_fingerprint = Column(String(64), nullable=False)
    row_version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    workspace = relationship("WorkspaceModel", back_populates="paper_groups")


class GroupMemberModel(Base):
    """Members of a paper group."""

    __tablename__ = "group_members"

    group_id = Column(String(64), ForeignKey("paper_groups.id", ondelete="CASCADE"), nullable=False)
    source_record_id = Column(String(64), ForeignKey("source_records.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("group_id", "source_record_id", name="pk_group_members"),
    )


class GroupSnapshotModel(Base):
    """Snapshot mapping of paper group to representative revision in a corpus revision."""

    __tablename__ = "group_snapshots"

    corpus_revision_id = Column(String(64), ForeignKey("corpus_revisions.id", ondelete="CASCADE"), nullable=False)
    group_id = Column(String(64), ForeignKey("paper_groups.id", ondelete="CASCADE"), nullable=False)
    representative_revision_id = Column(String(64), ForeignKey("record_revisions.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("corpus_revision_id", "group_id", name="pk_group_snapshots"),
    )


class GroupLineageModel(Base):
    """Provenance tracking for paper group mergers, splits, and extensions."""

    __tablename__ = "group_lineage"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    corpus_revision_id = Column(String(64), ForeignKey("corpus_revisions.id", ondelete="CASCADE"), nullable=False)
    parent_group_id = Column(String(64), ForeignKey("paper_groups.id", ondelete="CASCADE"), nullable=False)
    child_group_id = Column(String(64), ForeignKey("paper_groups.id", ondelete="CASCADE"), nullable=False)
    operation = Column(String(32), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)


class DedupEdgeModel(Base):
    """Deduplication pairwise candidate edge and evidence."""

    __tablename__ = "dedup_edges"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    record_id_a = Column(String(64), nullable=False)
    record_id_b = Column(String(64), nullable=False)
    score = Column(Float, nullable=False)
    method_version = Column(String(32), nullable=False)
    evidence_json = Column(Text, nullable=False)
    status = Column(String(32), nullable=False)
    reviewer_event_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("workspace_id", "record_id_a", "record_id_b", name="uq_dedup_edges_pair"),
    )


class MachineResultModel(Base):
    """Cached machine/rule output for a stage on a record revision."""

    __tablename__ = "machine_results"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    corpus_revision_id = Column(String(64), ForeignKey("corpus_revisions.id", ondelete="CASCADE"), nullable=False, index=True)
    group_id = Column(String(64), ForeignKey("paper_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    record_revision_id = Column(String(64), ForeignKey("record_revisions.id", ondelete="CASCADE"), nullable=False)
    stage = Column(String(32), nullable=False)
    input_fingerprint = Column(String(64), nullable=False)
    method_version = Column(String(32), nullable=False)
    output_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("stage", "input_fingerprint", "corpus_revision_id", name="uq_machine_results_fingerprint"),
    )


class ReviewEventModel(Base):
    """Append-only reviewer decision event."""

    __tablename__ = "review_events"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    group_id = Column(String(64), ForeignKey("paper_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    event_type = Column(String(32), nullable=False)
    payload_json = Column(Text, nullable=False)
    actor_id = Column(String(128), nullable=False)
    reason = Column(Text, nullable=True)
    supersedes_event_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    workspace = relationship("WorkspaceModel", back_populates="review_events")

    __table_args__ = (
        UniqueConstraint("workspace_id", "sequence", name="uq_review_events_workspace_seq"),
    )


class PicoAnnotationModel(Base):
    """Persistent PICO annotation offset spans bound to record revision text."""

    __tablename__ = "pico_annotations"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    event_id = Column(String(64), nullable=True)
    record_revision_id = Column(String(64), ForeignKey("record_revisions.id", ondelete="CASCADE"), nullable=False, index=True)
    label = Column(String(16), nullable=False)
    start_cp = Column(Integer, nullable=False)
    end_cp = Column(Integer, nullable=False)
    quote = Column(Text, nullable=False)
    provenance = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)


class ReviewConflictModel(Base):
    """Explicit review decision conflict awaiting resolution."""

    __tablename__ = "review_conflicts"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    corpus_revision_id = Column(String(64), ForeignKey("corpus_revisions.id", ondelete="CASCADE"), nullable=False, index=True)
    group_id = Column(String(64), ForeignKey("paper_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String(32), nullable=False)
    conflicting_event_ids_json = Column(Text, nullable=False)
    resolution_event_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)


class ExportModel(Base):
    """Export metadata and file record."""

    __tablename__ = "exports"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    corpus_revision_id = Column(String(64), ForeignKey("corpus_revisions.id", ondelete="CASCADE"), nullable=False, index=True)
    format = Column(String(16), nullable=False)
    record_count = Column(Integer, nullable=False)
    sha256_checksum = Column(String(64), nullable=False)
    file_path = Column(Text, nullable=False)
    created_by = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)


class EvidencePassportModel(Base):
    """Persistent auditable evidence-backed claim and validation record."""

    __tablename__ = "evidence_passports"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    paper_group_id = Column(String(64), ForeignKey("paper_groups.id", ondelete="CASCADE"), nullable=True, index=True)
    record_revision_id = Column(String(64), ForeignKey("record_revisions.id", ondelete="CASCADE"), nullable=False, index=True)
    claim_type = Column(String(32), nullable=False, index=True)
    claim_value = Column(Text, nullable=False)
    original_claim_value = Column(Text, nullable=True)
    source_field = Column(String(32), default="abstract", nullable=False)
    supporting_quote = Column(Text, nullable=False)
    start_cp = Column(Integer, nullable=True)
    end_cp = Column(Integer, nullable=True)
    source_fingerprint = Column(String(64), nullable=False)
    provenance = Column(String(64), nullable=False)
    validation_status = Column(String(32), nullable=False, index=True)
    validation_message = Column(Text, nullable=True)
    semantic_assessment = Column(String(32), default="unassessed", nullable=False)
    assessed_by = Column(String(128), nullable=True)
    is_contradictory = Column(Boolean, default=False, nullable=False)
    uncertainty_note = Column(Text, nullable=True)
    reviewer_correction_reason = Column(Text, nullable=True)
    superseded_by_id = Column(String(64), ForeignKey("evidence_passports.id", ondelete="SET NULL"), nullable=True)
    event_id = Column(String(64), ForeignKey("review_events.id", ondelete="SET NULL"), nullable=True)
    radar_status = Column(String(32), default="not_assessed", nullable=False, index=True)
    human_review_status = Column(String(32), default="unreviewed", nullable=False, index=True)
    reviewer_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    workspace = relationship("WorkspaceModel", back_populates="evidence_passports")

class DevilsAdvocateChallengeModel(Base):
    """Adversarial screening challenge to identify false exclusions and challenge fragile decisions."""

    __tablename__ = "devils_advocate_challenges"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    group_id = Column(String(64), ForeignKey("paper_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    record_revision_id = Column(String(64), ForeignKey("record_revisions.id", ondelete="CASCADE"), nullable=False, index=True)

    proposed_decision = Column(String(32), nullable=False)
    original_exclusion_reason = Column(Text, nullable=True)

    recommendation = Column(String(32), nullable=False, default="uphold_exclusion")
    vulnerability_score = Column(Float, nullable=False, default=0.0)
    critique = Column(Text, nullable=False)
    counter_arguments_json = Column(Text, nullable=False, default="[]")
    vulnerability_flags_json = Column(Text, nullable=False, default="[]")

    disposition = Column(String(32), nullable=False, default="pending", index=True)
    disposition_notes = Column(Text, nullable=True)
    disposition_by = Column(String(128), nullable=True)
    disposed_at = Column(DateTime, nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

class DuplicateMergeEventModel(Base):
    """Audited merge, split, and reversal operations with pre/post state and field provenance."""

    __tablename__ = "duplicate_merge_events"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    group_id = Column(String(64), ForeignKey("paper_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    canonical_record_id = Column(String(64), nullable=True)
    operation = Column(String(32), nullable=False)
    affected_source_ids_json = Column(Text, nullable=False, default="[]")
    match_evidence_json = Column(Text, nullable=False, default="{}")
    field_provenance_json = Column(Text, nullable=False, default="[]")
    pre_operation_state_json = Column(Text, nullable=False, default="{}")
    actor_id = Column(String(128), nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="active")
    reversal_event_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

