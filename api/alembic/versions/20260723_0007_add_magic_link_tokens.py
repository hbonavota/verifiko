"""Add magic_link_tokens table for passwordless sign-in.

Revision ID: 20260723_0007
Revises: 20260723_0006
Create Date: 2026-07-23 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260723_0007"
down_revision = "20260723_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "magic_link_tokens",
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("token_hash"),
    )
    op.create_index(
        "ix_magic_link_tokens_expires_at", "magic_link_tokens", ["expires_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_magic_link_tokens_expires_at", table_name="magic_link_tokens")
    op.drop_table("magic_link_tokens")
