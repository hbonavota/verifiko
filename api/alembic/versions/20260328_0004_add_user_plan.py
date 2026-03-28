"""Add user plan for authenticated quotas.

Revision ID: 20260328_0004
Revises: 20260328_0003
Create Date: 2026-03-28 20:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260328_0004"
down_revision = "20260328_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "plan",
                sa.String(length=32),
                nullable=False,
                server_default="FREE",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("plan")
