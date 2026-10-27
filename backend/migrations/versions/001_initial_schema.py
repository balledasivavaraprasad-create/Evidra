"""Initial foundation schema for workspaces, queries, records, jobs, and audit logs.

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-27 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. workspaces table
    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("current_revision_id", sa.String(length=64), nullable=True),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. criteria_versions table
    op.create_table(
        "criteria_versions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("pico_json", sa.Text(), nullable=False),
        sa.Column("criteria_json", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "sequence", name="uq_criteria_workspace_sequence"),
    )
    op.create_index("ix_criteria_versions_workspace_id", "criteria_versions", ["workspace_id"])

    # 3. query_versions table
    op.create_table(
        "query_versions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("parent_id", sa.String(length=64), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("ast_json", sa.Text(), nullable=False),
        sa.Column("start_date", sa.String(length=32), nullable=True),
        sa.Column("end_date", sa.String(length=32), nullable=True),
        sa.Column("sources_json", sa.Text(), nullable=False),
        sa.Column("criteria_version_id", sa.String(length=64), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["criteria_version_id"], ["criteria_versions.id"]),
        sa.ForeignKeyConstraint(["parent_id"], ["query_versions.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "sequence", name="uq_query_workspace_sequence"),
    )
    op.create_index("ix_query_versions_workspace_id", "query_versions", ["workspace_id"])

    # 4. search_executions table
    op.create_table(
        "search_executions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("query_version_id", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("exact_query", sa.Text(), nullable=False),
        sa.Column("synonym_setting", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("hit_count", sa.Integer(), nullable=False),
        sa.Column("counted_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("partial", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("cap", sa.Integer(), nullable=True),
        sa.Column("raw_hash", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["query_version_id"], ["query_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_search_executions_query_version_id", "search_executions", ["query_version_id"])

    # 5. source_records table
    op.create_table(
        "source_records",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_namespace", sa.String(length=64), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "source", "source_namespace", "external_id", name="uq_source_records_identity"),
    )
    op.create_index("ix_source_records_workspace_id", "source_records", ["workspace_id"])

    # 6. record_revisions table
    op.create_table(
        "record_revisions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("source_record_id", sa.String(length=64), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("abstract_text", sa.Text(), nullable=True),
        sa.Column("structured_sections_json", sa.Text(), nullable=True),
        sa.Column("authors_json", sa.Text(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("journal", sa.String(length=512), nullable=True),
        sa.Column("pages", sa.String(length=128), nullable=True),
        sa.Column("language_json", sa.Text(), nullable=True),
        sa.Column("publication_types_json", sa.Text(), nullable=True),
        sa.Column("doi", sa.String(length=256), nullable=True),
        sa.Column("pmid", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["source_record_id"], ["source_records.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_record_id", "content_hash", name="uq_record_revisions_content"),
    )
    op.create_index("ix_record_revisions_source_record_id", "record_revisions", ["source_record_id"])
    op.create_index("ix_record_revisions_doi", "record_revisions", ["doi"])
    op.create_index("ix_record_revisions_pmid", "record_revisions", ["pmid"])

    # 7. query_memberships table
    op.create_table(
        "query_memberships",
        sa.Column("search_execution_id", sa.String(length=64), nullable=False),
        sa.Column("source_record_id", sa.String(length=64), nullable=False),
        sa.Column("record_revision_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["record_revision_id"], ["record_revisions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["search_execution_id"], ["search_executions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_record_id"], ["source_records.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("search_execution_id", "source_record_id", name="pk_query_memberships"),
    )

    # 8. jobs table
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("request_key", sa.String(length=128), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("stage", sa.String(length=64), nullable=True),
        sa.Column("total_items", sa.Integer(), nullable=True),
        sa.Column("processed_items", sa.Integer(), nullable=True),
        sa.Column("error_json", sa.Text(), nullable=True),
        sa.Column("lease_owner", sa.String(length=128), nullable=True),
        sa.Column("lease_until", sa.DateTime(), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "request_key", name="uq_jobs_request_key"),
    )
    op.create_index("ix_jobs_workspace_id", "jobs", ["workspace_id"])

    # 9. runs table
    op.create_table(
        "runs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=True),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("input_hash", sa.String(length=64), nullable=True),
        sa.Column("output_hash", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_runs_workspace_id", "runs", ["workspace_id"])
    op.create_index("ix_runs_job_id", "runs", ["job_id"])

    # 10. idempotency_keys table
    op.create_table(
        "idempotency_keys",
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("endpoint", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("response_code", sa.Integer(), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_index("ix_idempotency_keys_workspace_id", "idempotency_keys", ["workspace_id"])


def downgrade() -> None:
    op.drop_table("idempotency_keys")
    op.drop_table("runs")
    op.drop_table("jobs")
    op.drop_table("query_memberships")
    op.drop_table("record_revisions")
    op.drop_table("source_records")
    op.drop_table("search_executions")
    op.drop_table("query_versions")
    op.drop_table("criteria_versions")
    op.drop_table("workspaces")
