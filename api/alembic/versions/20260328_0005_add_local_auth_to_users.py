"""Add local auth fields to users.

Revision ID: 20260328_0005
Revises: 20260328_0004
Create Date: 2026-03-28 23:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260328_0005"
down_revision = "20260328_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("google_subject", existing_type=sa.String(length=255), nullable=True)
        batch_op.add_column(sa.Column("password_hash", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("password_hash")
        batch_op.alter_column(
            "google_subject",
            existing_type=sa.String(length=255),
            nullable=False,
        )
