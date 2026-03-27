"""Add structured message metadata to signals.

Revision ID: 20260327_0002
Revises: 20260317_0001
Create Date: 2026-03-27 18:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260327_0002"
down_revision = "20260317_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("signals", sa.Column("message_key", sa.String(length=255), nullable=True))
    op.add_column("signals", sa.Column("message_params", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("signals", "message_params")
    op.drop_column("signals", "message_key")
