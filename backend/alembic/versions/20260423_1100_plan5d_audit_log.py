"""Plan 5d : audit_log table pour tracabilité des mutations.

Revision ID: a4d7e9f2b1c3
Revises: e1f2a3b4c5d6
Create Date: 2026-04-23 11:00:00

Contexte : audit trail finance-grade. Chaque mutation (create/update/delete)
sur une entité critique (User, Entity, BankAccount, Transaction, Commitment,
CategorizationRule, Counterparty, ForecastLine, ForecastScenario) insère une
ligne ici avec before/after/diff, user, IP, user-agent. Consultable via
GET /api/admin/audit-log (admin only). Rétention cible : 1 an.

Additif uniquement : pas d'ALTER sur les tables existantes.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "a4d7e9f2b1c3"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=False),
            primary_key=True,
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("user_email", sa.String(255), nullable=True),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("entity_type", sa.String(60), nullable=False),
        sa.Column("entity_id", sa.String(60), nullable=False),
        sa.Column(
            "before_json",
            sa.dialects.postgresql.JSONB,
            nullable=True,
        ),
        sa.Column(
            "after_json",
            sa.dialects.postgresql.JSONB,
            nullable=True,
        ),
        sa.Column(
            "diff_json",
            sa.dialects.postgresql.JSONB,
            nullable=True,
        ),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("request_id", sa.String(36), nullable=True),
        sa.CheckConstraint(
            "action IN ('create', 'update', 'delete')",
            name="ck_audit_log_action",
        ),
    )
    op.create_index(
        "idx_audit_occurred_at_desc",
        "audit_log",
        [sa.text("occurred_at DESC")],
    )
    op.create_index(
        "idx_audit_entity",
        "audit_log",
        ["entity_type", "entity_id", sa.text("occurred_at DESC")],
    )
    op.create_index(
        "idx_audit_user",
        "audit_log",
        ["user_id", sa.text("occurred_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("idx_audit_user", table_name="audit_log")
    op.drop_index("idx_audit_entity", table_name="audit_log")
    op.drop_index("idx_audit_occurred_at_desc", table_name="audit_log")
    op.drop_table("audit_log")
