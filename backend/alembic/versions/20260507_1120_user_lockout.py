"""F4 — Ajoute failed_login_attempts et locked_until sur users.

Revision ID: h0r1z0nf0400
Revises: h0r1z0nf0300
Create Date: 2026-05-07 11:20:00
"""
from __future__ import annotations
import sqlalchemy as sa
from alembic import op

revision = "h0r1z0nf0400"
down_revision = "h0r1z0nf0300"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "failed_login_attempts",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "locked_until",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")
