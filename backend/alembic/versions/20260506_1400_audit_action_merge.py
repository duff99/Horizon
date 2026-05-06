"""Élargit la contrainte ck_audit_log_action pour accepter "merge".

La fusion de tiers (refonte page Tiers, Plan A) loggue une entrée
audit avec action="merge" : c'est plus précis que "delete" + grep dans
le payload, et permet aux filtres de l'admin du journal d'audit de
remonter explicitement les fusions.

Revision ID: h0r1z0n50601
Revises: h0r1z0n50505
Create Date: 2026-05-06 14:00:00
"""
from __future__ import annotations

from alembic import op


revision = "h0r1z0n50601"
down_revision = "h0r1z0n50505"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE audit_log DROP CONSTRAINT IF EXISTS ck_audit_log_action")
    op.execute(
        "ALTER TABLE audit_log ADD CONSTRAINT ck_audit_log_action "
        "CHECK (action IN ('create', 'update', 'delete', 'merge'))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE audit_log DROP CONSTRAINT IF EXISTS ck_audit_log_action")
    op.execute(
        "ALTER TABLE audit_log ADD CONSTRAINT ck_audit_log_action "
        "CHECK (action IN ('create', 'update', 'delete'))"
    )
