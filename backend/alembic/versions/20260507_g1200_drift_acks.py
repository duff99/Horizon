"""G12 — Table drift_acks pour le snooze/acquittement de dérive.

Revision ID: h0r1z0ng1200
Revises: h0r1z0ne0500
Create Date: 2026-05-07 12:00:00
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "h0r1z0ng1200"
down_revision = "h0r1z0ne0500"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "drift_acks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "entity_id",
            sa.Integer(),
            sa.ForeignKey("entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "category_id",
            sa.Integer(),
            sa.ForeignKey("categories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("snoozed_until", sa.Date(), nullable=False),
        sa.Column(
            "acknowledged_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "acknowledged_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("note", sa.String(500), nullable=True),
    )
    op.create_index(
        "ix_drift_acks_entity_category", "drift_acks", ["entity_id", "category_id"]
    )
    op.create_index("ix_drift_acks_snoozed_until", "drift_acks", ["snoozed_until"])


def downgrade() -> None:
    op.drop_index("ix_drift_acks_snoozed_until", table_name="drift_acks")
    op.drop_index("ix_drift_acks_entity_category", table_name="drift_acks")
    op.drop_table("drift_acks")
