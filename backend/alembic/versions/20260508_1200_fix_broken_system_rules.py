"""F6 — Correction des règles system cassées par normalize_label.

Revision ID: h0r1z0nf0600
Revises: h0r1z0nf0400
Create Date: 2026-05-08 12:00:00

Deux règles system avaient un label_value qui ne survivait pas à la
normalisation appliquée à la colonne `Transaction.normalized_label` :

- id=99 "Anthropic / Claude.ai" : label_value="ANTHROPIC, CLAUDE.AI"
  Les patterns sont split par virgule puis comparés via ilike contre
  normalized_label (qui n'a plus de point). "CLAUDE.AI" ne matche jamais.
  Fix : `ANTHROPIC, CLAUDE AI` (forme post-normalize).

- id=103 "Frais bancaires divers (Frais **)" : label_value="FRAIS **",
  operator STARTS_WITH. normalized_label n'a jamais d'astérisque.
  Fix : STARTS_WITH "FRAIS BANCAIRES" (matche FRAIS BANCAIRES DIVERS,
  FRAIS BANCAIRES SUR PAIEMENT, etc.). Choix conservateur — on évite un
  STARTS_WITH "FRAIS" qui capturerait des flux non bancaires (ex. frais
  de port).
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "h0r1z0nf0600"
down_revision = "h0r1z0nf0400"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # Rule 99 — Anthropic / Claude.ai
    bind.execute(
        sa.text(
            "UPDATE categorization_rules "
            "SET label_value = :v, updated_at = NOW() "
            "WHERE id = 99 AND label_value = 'ANTHROPIC, CLAUDE.AI'"
        ),
        {"v": "ANTHROPIC, CLAUDE AI"},
    )
    # Rule 103 — Frais bancaires
    bind.execute(
        sa.text(
            "UPDATE categorization_rules "
            "SET label_value = :v, updated_at = NOW() "
            "WHERE id = 103 AND label_value = 'FRAIS **'"
        ),
        {"v": "FRAIS BANCAIRES"},
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE categorization_rules SET label_value = 'ANTHROPIC, CLAUDE.AI' "
            "WHERE id = 99 AND label_value = 'ANTHROPIC, CLAUDE AI'"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE categorization_rules SET label_value = 'FRAIS **' "
            "WHERE id = 103 AND label_value = 'FRAIS BANCAIRES'"
        )
    )
