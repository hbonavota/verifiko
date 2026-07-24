"""Add screenshot_ref to verification_jobs for detonation screenshots (B.3b).

Stores the R2 object key of the screenshot captured during headless detonation.
Nullable: only async scans that detonate with screenshot storage enabled ever
populate it; every other job leaves it NULL.

Revision ID: 20260724_0009
Revises: 20260724_0008
Create Date: 2026-07-24 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260724_0009"
down_revision = "20260724_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "verification_jobs",
        sa.Column("screenshot_ref", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("verification_jobs", "screenshot_ref")
