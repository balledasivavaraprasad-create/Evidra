"""Add missing evidence radar fields to evidence_passports.

Revision ID: 005_missing_evidence_radar
Revises: 004_search_evolution
Create Date: 2026-10-28 13:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "005_missing_evidence_radar"
down_revision: Union[str, None] = "004_search_evolution"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("evidence_passports", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("radar_status", sa.String(length=32), server_default="not_assessed", nullable=False)
        )
        batch_op.add_column(
            sa.Column("human_review_status", sa.String(length=32), server_default="unreviewed", nullable=False)
        )
        batch_op.add_column(
            sa.Column("reviewer_notes", sa.Text(), nullable=True)
        )
        batch_op.create_index("ix_evidence_passports_radar_status", ["radar_status"], unique=False)
        batch_op.create_index("ix_evidence_passports_human_review_status", ["human_review_status"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("evidence_passports", schema=None) as batch_op:
        batch_op.drop_index("ix_evidence_passports_human_review_status")
        batch_op.drop_index("ix_evidence_passports_radar_status")
        batch_op.drop_column("reviewer_notes")
        batch_op.drop_column("human_review_status")
        batch_op.drop_column("radar_status")
