"""Plan 5 : table forecast_entries (prévisionnel manuel de trésorerie).

Revision ID: f7a8b9c0d1e2
Revises: e5f6a7b8c9d0
Create Date: 2026-04-20 11:00:00
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "f7a8b9c0d1e2"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    recurrence_enum = sa.Enum(
        "NONE", "WEEKLY", "MONTHLY", "QUARTERLY", "YEARLY",
        name="forecast_recurrence",
    )

    op.create_table(
        "forecast_entries",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "entity_id",
            sa.Integer,
            sa.ForeignKey("entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "bank_account_id",
            sa.Integer,
            sa.ForeignKey("bank_accounts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column(
            "category_id",
            sa.Integer,
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "counterparty_id",
            sa.Integer,
            sa.ForeignKey("counterparties.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "recurrence",
            recurrence_enum,
            nullable=False,
            server_default="NONE",
        ),
        sa.Column("recurrence_until", sa.Date, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_by_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_forecast_entity_due", "forecast_entries", ["entity_id", "due_date"]
    )


def downgrade() -> None:
    op.drop_index("ix_forecast_entity_due", table_name="forecast_entries")
    op.drop_table("forecast_entries")
    sa.Enum(name="forecast_recurrence").drop(op.get_bind(), checkfirst=True)
