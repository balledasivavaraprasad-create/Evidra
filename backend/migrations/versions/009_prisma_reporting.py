"""Add prisma_snapshots table for persistent PRISMA 2020 flow report versions.

Revision ID: 009_prisma_reporting
Revises: 008_users_and_ownership
Create Date: 2026-10-29 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "009_prisma_reporting"
down_revision: Union[str, None] = "008_users_and_ownership"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "prisma_snapshots",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(length=64),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("corpus_revision_id", sa.String(length=64), nullable=True),
        sa.Column("query_version_id", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=256), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("schema_version", sa.String(length=32), nullable=False, server_default="2020.1"),
        sa.Column("counts_json", sa.Text(), nullable=False),
        sa.Column("exclusion_reasons_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("validation_issues_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_by", sa.String(length=128), nullable=False, server_default="reviewer"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_prisma_snapshots_workspace_id",
        "prisma_snapshots",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_prisma_snapshots_corpus_revision_id",
        "prisma_snapshots",
        ["corpus_revision_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_prisma_snapshots_corpus_revision_id", table_name="prisma_snapshots")
    op.drop_index("ix_prisma_snapshots_workspace_id", table_name="prisma_snapshots")
    op.drop_table("prisma_snapshots")
