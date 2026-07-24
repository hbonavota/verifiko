"""Add verification_jobs table for durable async scan state.

Moves scan job state off Redis and into the primary database so it is shared
across serverless invocations and independent of the Redis command quota.

Revision ID: 20260724_0008
Revises: 20260723_0007
Create Date: 2026-07-24 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260724_0008"
down_revision = "20260723_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "verification_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_user_id", sa.String(length=36), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("result_verification_id", sa.String(length=36), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("webhook_url", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_verification_jobs_owner_user_id", "verification_jobs", ["owner_user_id"]
    )
    op.create_index("ix_verification_jobs_status", "verification_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_verification_jobs_status", table_name="verification_jobs")
    op.drop_index("ix_verification_jobs_owner_user_id", table_name="verification_jobs")
    op.drop_table("verification_jobs")
