"""plan1: seed minimal categories

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


CATEGORIES = [
    # (slug, name, color, parent_slug, is_system)
    ("encaissements",              "Encaissements",                  "#2ecc71", None, True),
    ("decaissements-personnel",    "Décaissements — Personnel",      "#e74c3c", None, True),
    ("decaissements-sous-traitants","Décaissements — Sous-traitants", "#e67e22", None, True),
    ("decaissements-fournisseurs", "Décaissements — Fournisseurs",   "#d35400", None, True),
    ("charges-sociales-taxes",     "Charges sociales & taxes",       "#8e44ad", None, True),
    ("frais-bancaires",            "Frais bancaires",                "#34495e", None, True),
    ("honoraires-juridiques",      "Honoraires juridiques",          "#16a085", None, True),
    ("flux-intergroupe",           "Flux intergroupe",               "#2980b9", None, True),
    ("non-categorisees",           "Non catégorisées",               "#95a5a6", None, True),
]


def upgrade() -> None:
    bind = op.get_bind()
    # Insertion racines
    slug_to_id: dict[str, int] = {}
    for slug, name, color, parent_slug, is_system in CATEGORIES:
        parent_id = slug_to_id.get(parent_slug) if parent_slug else None
        result = bind.execute(
            sa.text(
                "INSERT INTO categories (name, slug, color, parent_category_id, is_system) "
                "VALUES (:name, :slug, :color, :parent_id, :is_system) RETURNING id"
            ),
            {"name": name, "slug": slug, "color": color,
             "parent_id": parent_id, "is_system": is_system},
        )
        slug_to_id[slug] = result.scalar_one()


def downgrade() -> None:
    op.execute("DELETE FROM categories WHERE is_system = TRUE")
