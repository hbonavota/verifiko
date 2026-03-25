"""Initial verification persistence schema.

Revision ID: 20260317_0001
Revises: None
Create Date: 2026-03-17 00:00:01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260317_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "verifications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("original_input", sa.Text(), nullable=False),
        sa.Column("normalized_input", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("calculation_version", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_verifications_created_at",
        "verifications",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_verifications_status",
        "verifications",
        ["status"],
        unique=False,
    )

    op.create_table(
        "risk_assessments",
        sa.Column("verification_id", sa.String(length=36), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("verdict", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("top_signals", sa.JSON(), nullable=False),
        sa.Column("category_breakdown", sa.JSON(), nullable=False),
        sa.Column("terminal_override", sa.Boolean(), nullable=False),
        sa.Column("terminal_reason", sa.Text(), nullable=True),
        sa.Column("calculation_version", sa.String(length=32), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["verification_id"],
            ["verifications.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("verification_id"),
    )

    op.create_table(
        "signals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("verification_id", sa.String(length=36), nullable=False),
        sa.Column("signal_type", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("detected", sa.Boolean(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("base_weight", sa.Float(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["verification_id"],
            ["verifications.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_signals_verification_id",
        "signals",
        ["verification_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_signals_verification_id", table_name="signals")
    op.drop_table("signals")
    op.drop_table("risk_assessments")
    op.drop_index("ix_verifications_status", table_name="verifications")
    op.drop_index("ix_verifications_created_at", table_name="verifications")
    op.drop_table("verifications")
