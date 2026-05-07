"""E5 — Ajout colonne acknowledged_at sur client_errors.

Revision ID: h0r1z0ne0500
Revises: h0r1z0ne0200
Create Date: 2026-05-07 20:20:00
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "h0r1z0ne0500"
down_revision = "h0r1z0ne0200"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "client_errors",
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("client_errors", "acknowledged_at")
