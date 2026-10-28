"""Add devils_advocate_challenges table.

Revision ID: 006_devils_advocate
Revises: 005_missing_evidence_radar
Create Date: 2026-10-28 13:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "006_devils_advocate"
down_revision: Union[str, None] = "005_missing_evidence_radar"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "devils_advocate_challenges",
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
        sa.Column(
            "record_revision_id",
            sa.String(length=64),
            sa.ForeignKey("record_revisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("proposed_decision", sa.String(length=32), nullable=False),
        sa.Column("original_exclusion_reason", sa.Text(), nullable=True),
        sa.Column(
            "recommendation",
            sa.String(length=32),
            server_default="uphold_exclusion",
            nullable=False,
        ),
        sa.Column(
            "vulnerability_score",
            sa.Float(),
            server_default="0.0",
            nullable=False,
        ),
        sa.Column("critique", sa.Text(), nullable=False),
        sa.Column(
            "counter_arguments_json",
            sa.Text(),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "vulnerability_flags_json",
            sa.Text(),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "disposition",
            sa.String(length=32),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("disposition_notes", sa.Text(), nullable=True),
        sa.Column("disposition_by", sa.String(length=128), nullable=True),
        sa.Column("disposed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_devils_advocate_challenges_workspace_id",
        "devils_advocate_challenges",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_devils_advocate_challenges_group_id",
        "devils_advocate_challenges",
        ["group_id"],
        unique=False,
    )
    op.create_index(
        "ix_devils_advocate_challenges_disposition",
        "devils_advocate_challenges",
        ["disposition"],
        unique=False,
    )
    op.create_index(
        "ix_devils_advocate_challenges_vulnerability_score",
        "devils_advocate_challenges",
        ["vulnerability_score"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_devils_advocate_challenges_vulnerability_score",
        table_name="devils_advocate_challenges",
    )
    op.drop_index(
        "ix_devils_advocate_challenges_disposition",
        table_name="devils_advocate_challenges",
    )
    op.drop_index(
        "ix_devils_advocate_challenges_group_id",
        table_name="devils_advocate_challenges",
    )
    op.drop_index(
        "ix_devils_advocate_challenges_workspace_id",
        table_name="devils_advocate_challenges",
    )
    op.drop_table("devils_advocate_challenges")
