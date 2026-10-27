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
