"""Add search evolution fields to query_versions.

Revision ID: 004_search_evolution
Revises: 003_evidence_passport
Create Date: 2026-10-28 12:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "004_search_evolution"
down_revision: Union[str, None] = "003_evidence_passport"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("query_versions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("change_description", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("restored_from_version_id", sa.String(length=64), nullable=True))
        batch_op.create_foreign_key(
            "fk_query_versions_restored_from",
            "query_versions",
            ["restored_from_version_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("query_versions", schema=None) as batch_op:
        batch_op.drop_constraint("fk_query_versions_restored_from", type_="foreignkey")
        batch_op.drop_column("restored_from_version_id")
        batch_op.drop_column("change_description")
