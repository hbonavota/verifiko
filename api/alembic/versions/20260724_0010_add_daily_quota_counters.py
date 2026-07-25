"""Add daily_quota_counters for Postgres-backed daily verification quota.

Moves the daily verification quota off Redis and into the primary database so the
counter is durable, consistent across serverless invocations, and independent of
the Redis command quota. Incremented via an atomic conditional UPSERT.

Revision ID: 20260724_0010
Revises: 20260724_0009
Create Date: 2026-07-24 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260724_0010"
down_revision = "20260724_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "daily_quota_counters",
        sa.Column("identity_key", sa.String(length=255), nullable=False),
        sa.Column("quota_day", sa.Date(), nullable=False),
        sa.Column("used", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("identity_key", "quota_day"),
    )


def downgrade() -> None:
    op.drop_table("daily_quota_counters")
