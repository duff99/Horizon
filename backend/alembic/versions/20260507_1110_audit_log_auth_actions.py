"""F3 — Étend la CheckConstraint audit_log action pour accepter login/login_failed/logout.

Revision ID: h0r1z0nf0300
Revises: h0r1z0nf0100
Create Date: 2026-05-07 11:10:00
"""
from __future__ import annotations
from alembic import op

revision = "h0r1z0nf0300"
down_revision = "h0r1z0nf0100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_audit_log_action", "audit_log")
    op.create_check_constraint(
        "ck_audit_log_action",
        "audit_log",
        "action IN ('create','update','delete','merge','login','login_failed','logout')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_audit_log_action", "audit_log")
    op.create_check_constraint(
        "ck_audit_log_action",
        "audit_log",
        "action IN ('create','update','delete','merge')",
    )
