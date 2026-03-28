"""Add users and verification ownership.

Revision ID: 20260328_0003
Revises: 20260327_0002
Create Date: 2026-03-28 12:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260328_0003"
down_revision = "20260327_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("google_subject", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("google_subject"),
    )
    op.create_index("ix_users_created_at", "users", ["created_at"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_index("ix_users_google_subject", "users", ["google_subject"], unique=False)

    with op.batch_alter_table("verifications") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.String(length=36), nullable=True))
        batch_op.create_index("ix_verifications_user_id", ["user_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_verifications_user_id_users",
            "users",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("verifications") as batch_op:
        batch_op.drop_constraint("fk_verifications_user_id_users", type_="foreignkey")
        batch_op.drop_index("ix_verifications_user_id")
        batch_op.drop_column("user_id")

    op.drop_index("ix_users_google_subject", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_created_at", table_name="users")
    op.drop_table("users")
