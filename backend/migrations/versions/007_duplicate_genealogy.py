"""Add duplicate_merge_events table for genealogy, split, and reversal tracking.

Revision ID: 007_duplicate_genealogy
Revises: 006_devils_advocate
Create Date: 2026-10-28 14:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "007_duplicate_genealogy"
down_revision: Union[str, None] = "006_devils_advocate"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "duplicate_merge_events",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(length=64),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "group_id",
            sa.String(length=64),
            sa.ForeignKey("paper_groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("canonical_record_id", sa.String(length=64), nullable=True),
        sa.Column("operation", sa.String(length=32), nullable=False),
        sa.Column(
            "affected_source_ids_json",
            sa.Text(),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "match_evidence_json",
            sa.Text(),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "field_provenance_json",
            sa.Text(),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "pre_operation_state_json",
            sa.Text(),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="active",
            nullable=False,
        ),
        sa.Column("reversal_event_id", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_duplicate_merge_events_workspace_id",
        "duplicate_merge_events",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_duplicate_merge_events_group_id",
        "duplicate_merge_events",
        ["group_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_duplicate_merge_events_group_id",
        table_name="duplicate_merge_events",
    )
    op.drop_index(
        "ix_duplicate_merge_events_workspace_id",
        table_name="duplicate_merge_events",
    )
    op.drop_table("duplicate_merge_events")
