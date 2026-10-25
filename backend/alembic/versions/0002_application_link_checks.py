"""Record the last automated check of each scheme's application link

Revision ID: 0002_application_link_checks
Revises: 5bb0abe97c7b
Create Date: 2026-10-22
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_application_link_checks"
down_revision: str | None = "5bb0abe97c7b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("scheme_versions", sa.Column("application_url_http_status", sa.Integer(), nullable=True))
    op.add_column(
        "scheme_versions",
        sa.Column("application_url_checked_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scheme_versions", "application_url_checked_at")
    op.drop_column("scheme_versions", "application_url_http_status")
