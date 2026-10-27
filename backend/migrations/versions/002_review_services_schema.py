"""Add review services schema: corpus revisions, paper groups, review events, dedup edges, PICO annotations, and exports.

Revision ID: 002_review_services_schema
Revises: 001_initial_schema
Create Date: 2026-10-28 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002_review_services_schema"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. corpus_revisions
    op.create_table(
        "corpus_revisions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("parent_id", sa.String(length=64), nullable=True),
        sa.Column("criteria_version_id", sa.String(length=64), nullable=False),
        sa.Column("dedup_version", sa.String(length=32), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("decision_seq_cutoff", sa.Integer(), nullable=True),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("group_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("record_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["corpus_revisions.id"]),
        sa.ForeignKeyConstraint(["criteria_version_id"], ["criteria_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_corpus_revisions_workspace_id", "corpus_revisions", ["workspace_id"])

    # 2. corpus_queries
    op.create_table(
        "corpus_queries",
        sa.Column("corpus_revision_id", sa.String(length=64), nullable=False),
        sa.Column("search_execution_id", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["corpus_revision_id"], ["corpus_revisions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["search_execution_id"], ["search_executions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("corpus_revision_id", "search_execution_id", name="pk_corpus_queries"),
    )

    # 3. corpus_members
    op.create_table(
        "corpus_members",
        sa.Column("corpus_revision_id", sa.String(length=64), nullable=False),
        sa.Column("source_record_id", sa.String(length=64), nullable=False),
        sa.Column("record_revision_id", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["corpus_revision_id"], ["corpus_revisions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_record_id"], ["source_records.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["record_revision_id"], ["record_revisions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("corpus_revision_id", "source_record_id", name="pk_corpus_members"),
    )

    # 4. paper_groups
    op.create_table(
        "paper_groups",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("membership_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_paper_groups_workspace_id", "paper_groups", ["workspace_id"])

    # 5. group_members
    op.create_table(
        "group_members",
        sa.Column("group_id", sa.String(length=64), nullable=False),
        sa.Column("source_record_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["paper_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_record_id"], ["source_records.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("group_id", "source_record_id", name="pk_group_members"),
    )

    # 6. group_snapshots
    op.create_table(
        "group_snapshots",
        sa.Column("corpus_revision_id", sa.String(length=64), nullable=False),
        sa.Column("group_id", sa.String(length=64), nullable=False),
        sa.Column("representative_revision_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["corpus_revision_id"], ["corpus_revisions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["paper_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["representative_revision_id"], ["record_revisions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("corpus_revision_id", "group_id", name="pk_group_snapshots"),
    )

    # 7. group_lineage
    op.create_table(
        "group_lineage",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("corpus_revision_id", sa.String(length=64), nullable=False),
        sa.Column("parent_group_id", sa.String(length=64), nullable=False),
        sa.Column("child_group_id", sa.String(length=64), nullable=False),
        sa.Column("operation", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["corpus_revision_id"], ["corpus_revisions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_group_id"], ["paper_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["child_group_id"], ["paper_groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 8. dedup_edges
    op.create_table(
        "dedup_edges",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("record_id_a", sa.String(length=64), nullable=False),
        sa.Column("record_id_b", sa.String(length=64), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("method_version", sa.String(length=32), nullable=False),
        sa.Column("evidence_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reviewer_event_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "record_id_a", "record_id_b", name="uq_dedup_edges_pair"),
    )
    op.create_index("ix_dedup_edges_workspace_id", "dedup_edges", ["workspace_id"])

    # 9. machine_results
    op.create_table(
        "machine_results",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("corpus_revision_id", sa.String(length=64), nullable=False),
        sa.Column("group_id", sa.String(length=64), nullable=False),
        sa.Column("record_revision_id", sa.String(length=64), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("method_version", sa.String(length=32), nullable=False),
        sa.Column("output_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["corpus_revision_id"], ["corpus_revisions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["paper_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["record_revision_id"], ["record_revisions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stage", "input_fingerprint", "corpus_revision_id", name="uq_machine_results_fingerprint"),
    )
    op.create_index("ix_machine_results_corpus_revision_id", "machine_results", ["corpus_revision_id"])
    op.create_index("ix_machine_results_group_id", "machine_results", ["group_id"])

    # 10. review_events
    op.create_table(
        "review_events",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("group_id", sa.String(length=64), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("supersedes_event_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["paper_groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "sequence", name="uq_review_events_workspace_seq"),
    )
    op.create_index("ix_review_events_workspace_id", "review_events", ["workspace_id"])
    op.create_index("ix_review_events_group_id", "review_events", ["group_id"])

    # 11. pico_annotations
    op.create_table(
        "pico_annotations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("event_id", sa.String(length=64), nullable=True),
        sa.Column("record_revision_id", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=16), nullable=False),
        sa.Column("start_cp", sa.Integer(), nullable=False),
        sa.Column("end_cp", sa.Integer(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("provenance", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["record_revision_id"], ["record_revisions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pico_annotations_record_revision_id", "pico_annotations", ["record_revision_id"])

    # 12. review_conflicts
    op.create_table(
        "review_conflicts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("corpus_revision_id", sa.String(length=64), nullable=False),
        sa.Column("group_id", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("conflicting_event_ids_json", sa.Text(), nullable=False),
        sa.Column("resolution_event_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["corpus_revision_id"], ["corpus_revisions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["paper_groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_conflicts_corpus_revision_id", "review_conflicts", ["corpus_revision_id"])
    op.create_index("ix_review_conflicts_group_id", "review_conflicts", ["group_id"])

    # 13. exports
    op.create_table(
        "exports",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("corpus_revision_id", sa.String(length=64), nullable=False),
        sa.Column("format", sa.String(length=16), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("sha256_checksum", sa.String(length=64), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["corpus_revision_id"], ["corpus_revisions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_exports_workspace_id", "exports", ["workspace_id"])
    op.create_index("ix_exports_corpus_revision_id", "exports", ["corpus_revision_id"])


def downgrade() -> None:
    op.drop_table("exports")
    op.drop_table("review_conflicts")
    op.drop_table("pico_annotations")
    op.drop_table("review_events")
    op.drop_table("machine_results")
    op.drop_table("dedup_edges")
    op.drop_table("group_lineage")
    op.drop_table("group_snapshots")
    op.drop_table("group_members")
    op.drop_table("paper_groups")
    op.drop_table("corpus_members")
    op.drop_table("corpus_queries")
    op.drop_table("corpus_revisions")
