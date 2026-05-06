"""Ajoute la valeur SINGLE_MONTH_FIXED à l'enum forecast_line_method.

Permet de saisir un montant prévisionnel ponctuel sur un seul mois (ex.
encaissement client exceptionnel en juillet 2026), sans qu'il se répète
chaque mois comme RECURRING_FIXED.

Revision ID: h0r1z0n50505
Revises: h0r1z0n50504
Create Date: 2026-05-05 15:20:00
"""
from __future__ import annotations

from alembic import op


revision = "h0r1z0n50505"
down_revision = "h0r1z0n50504"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ADD VALUE doit être hors transaction sur certaines versions.
    # Sur Postgres 12+ c'est OK en transaction sauf si la valeur est utilisée
    # dans la même transaction. Ici on ne l'utilise pas, donc safe.
    op.execute("ALTER TYPE forecast_line_method ADD VALUE IF NOT EXISTS 'SINGLE_MONTH_FIXED'")


def downgrade() -> None:
    # Postgres ne supporte pas ALTER TYPE DROP VALUE. On laisse la valeur
    # orpheline ; tant qu'aucune ligne ne l'utilise, c'est sans effet.
    pass
