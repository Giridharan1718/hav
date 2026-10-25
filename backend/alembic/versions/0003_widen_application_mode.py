"""Widen application_mode to fit descriptive modes

Revision ID: 0003_widen_application_mode
Revises: 0002_application_link_checks
Create Date: 2026-10-22
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_widen_application_mode"
down_revision: str | None = "0002_application_link_checks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "scheme_versions",
        "application_mode",
        existing_type=sa.String(length=60),
        type_=sa.String(length=160),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "scheme_versions",
        "application_mode",
        existing_type=sa.String(length=160),
        type_=sa.String(length=60),
        existing_nullable=True,
    )
