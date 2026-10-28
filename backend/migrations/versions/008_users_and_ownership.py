"""Add user accounts, review ownership, job payloads, and persisted import selection.

Revision ID: 008_users_and_ownership
Revises: 007_duplicate_genealogy
Create Date: 2026-10-29 04:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_users_and_ownership"
down_revision: Union[str, None] = "007_duplicate_genealogy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("google_sub", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("google_sub", name="uq_users_google_sub"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    with op.batch_alter_table("workspaces", schema=None) as batch_op:
        batch_op.add_column(sa.Column("owner_user_id", sa.String(length=64), nullable=True))
        batch_op.create_foreign_key(
            "fk_workspaces_owner_user_id", "users", ["owner_user_id"], ["id"], ondelete="CASCADE"
        )
        batch_op.create_index("ix_workspaces_owner_user_id", ["owner_user_id"], unique=False)

    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("payload_json", sa.Text(), nullable=True))

    with op.batch_alter_table("search_executions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("selected_for_import", sa.Boolean(), nullable=False, server_default=sa.true())
        )


def downgrade() -> None:
    with op.batch_alter_table("search_executions", schema=None) as batch_op:
        batch_op.drop_column("selected_for_import")
    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.drop_column("payload_json")
    with op.batch_alter_table("workspaces", schema=None) as batch_op:
        batch_op.drop_index("ix_workspaces_owner_user_id")
        batch_op.drop_constraint("fk_workspaces_owner_user_id", type_="foreignkey")
        batch_op.drop_column("owner_user_id")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
