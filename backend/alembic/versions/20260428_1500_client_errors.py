"""Table `client_errors` : remontée des erreurs JS/fetch côté frontend.

Revision ID: c1e7f0a4b8d9
Revises: a4d7e9f2b1c3
Create Date: 2026-04-28 15:00:00

Contexte : pour avoir un canal de remontée des bugs front automatique
(plutôt que de dépendre d'un copier/coller de la console Chrome par
l'utilisateur), on persiste les erreurs en DB. Capture côté client :
window.onerror, unhandledrejection, et l'intercepteur apiFetch.
Rétention 30j (cleanup déclenché côté script ou via cron).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "c1e7f0a4b8d9"
down_revision = "a4d7e9f2b1c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "client_errors",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("severity", sa.String(20), nullable=False, server_default="error"),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("stack", sa.Text, nullable=True),
        sa.Column("url", sa.Text, nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("context_json", sa.dialects.postgresql.JSONB, nullable=True),
        sa.CheckConstraint(
            "severity IN ('debug', 'info', 'warning', 'error', 'fatal')",
            name="ck_client_errors_severity",
        ),
        sa.CheckConstraint(
            "source IN ('window.onerror', 'unhandledrejection', 'console.error', 'apifetch', 'manual')",
            name="ck_client_errors_source",
        ),
    )
    op.create_index(
        "ix_client_errors_occurred_at",
        "client_errors",
        ["occurred_at"],
    )
    op.create_index(
        "ix_client_errors_user_id",
        "client_errors",
        ["user_id"],
    )
    op.create_index(
        "ix_client_errors_severity",
        "client_errors",
        ["severity"],
    )


def downgrade() -> None:
    op.drop_index("ix_client_errors_severity", table_name="client_errors")
    op.drop_index("ix_client_errors_user_id", table_name="client_errors")
    op.drop_index("ix_client_errors_occurred_at", table_name="client_errors")
    op.drop_table("client_errors")
