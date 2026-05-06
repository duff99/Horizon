"""Ajoute la sous-catégorie "Prélèvement à la source" sous Impôts & taxes.

Le prélèvement à la source (PAS-DSN) est une retenue d'impôt sur le revenu
collectée par l'employeur sur les salaires, puis reversée à la DGFIP. Avant
cette migration les transactions DGFIP IMPOT-PAS-DSN étaient catégorisées
en "Impôt sur les sociétés" (faux positif de la règle DGFIP générique).

Revision ID: h0r1z0n50501
Revises: f3d2c1b0a987
Create Date: 2026-05-05 12:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "h0r1z0n50501"
down_revision = "f3d2c1b0a987"
branch_labels = None
depends_on = None


NEW_SLUG = "prelevement-source"
NEW_NAME = "Prélèvement à la source"
NEW_COLOR = "#a04000"
PARENT_SLUG = "impots-taxes"


def upgrade() -> None:
    conn = op.get_bind()

    parent_id = conn.execute(
        sa.text("SELECT id FROM categories WHERE slug = :s"),
        {"s": PARENT_SLUG},
    ).scalar_one_or_none()
    if parent_id is None:
        raise RuntimeError(
            f"Catégorie parent '{PARENT_SLUG}' introuvable, migration plan2 absente ?"
        )

    exists = conn.execute(
        sa.text("SELECT id FROM categories WHERE slug = :s"),
        {"s": NEW_SLUG},
    ).scalar_one_or_none()
    if exists:
        return

    conn.execute(
        sa.text(
            "INSERT INTO categories "
            "(name, slug, color, parent_category_id, is_system, created_at) "
            "VALUES (:name, :slug, :color, :parent, true, NOW())"
        ),
        {
            "name": NEW_NAME,
            "slug": NEW_SLUG,
            "color": NEW_COLOR,
            "parent": parent_id,
        },
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM categories WHERE slug = :s"),
        {"s": NEW_SLUG},
    )
