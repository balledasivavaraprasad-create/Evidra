"""Add Evidence Passport schema for auditable AI and human claims.

Revision ID: 003_evidence_passport
Revises: 002_review_services_schema
Create Date: 2026-10-28 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "003_evidence_passport"
down_revision: Union[str, None] = "002_review_services_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "evidence_passports",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("paper_group_id", sa.String(length=64), nullable=True),
        sa.Column("record_revision_id", sa.String(length=64), nullable=False),
        sa.Column("claim_type", sa.String(length=32), nullable=False),
        sa.Column("claim_value", sa.Text(), nullable=False),
        sa.Column("original_claim_value", sa.Text(), nullable=True),
        sa.Column("source_field", sa.String(length=32), server_default="abstract", nullable=False),
        sa.Column("supporting_quote", sa.Text(), nullable=False),
        sa.Column("start_cp", sa.Integer(), nullable=True),
        sa.Column("end_cp", sa.Integer(), nullable=True),
        sa.Column("source_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("provenance", sa.String(length=64), nullable=False),
        sa.Column("validation_status", sa.String(length=32), nullable=False),
        sa.Column("validation_message", sa.Text(), nullable=True),
        sa.Column("semantic_assessment", sa.String(length=32), server_default="unassessed", nullable=False),
        sa.Column("assessed_by", sa.String(length=128), nullable=True),
        sa.Column("is_contradictory", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("uncertainty_note", sa.Text(), nullable=True),
        sa.Column("reviewer_correction_reason", sa.Text(), nullable=True),
        sa.Column("superseded_by_id", sa.String(length=64), nullable=True),
        sa.Column("event_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["paper_group_id"], ["paper_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["record_revision_id"], ["record_revisions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["superseded_by_id"], ["evidence_passports.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["event_id"], ["review_events.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidence_passports_workspace_id", "evidence_passports", ["workspace_id"])
    op.create_index("ix_evidence_passports_paper_group_id", "evidence_passports", ["paper_group_id"])
    op.create_index("ix_evidence_passports_record_revision_id", "evidence_passports", ["record_revision_id"])
    op.create_index("ix_evidence_passports_claim_type", "evidence_passports", ["claim_type"])
    op.create_index("ix_evidence_passports_validation_status", "evidence_passports", ["validation_status"])


def downgrade() -> None:
    op.drop_index("ix_evidence_passports_validation_status", table_name="evidence_passports")
    op.drop_index("ix_evidence_passports_claim_type", table_name="evidence_passports")
    op.drop_index("ix_evidence_passports_record_revision_id", table_name="evidence_passports")
    op.drop_index("ix_evidence_passports_paper_group_id", table_name="evidence_passports")
    op.drop_index("ix_evidence_passports_workspace_id", table_name="evidence_passports")
    op.drop_table("evidence_passports")
