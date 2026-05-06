"""Crée 3 sous-catégories métier identifiées lors de l'audit data 2026-05-05 :

- "Produits financiers" sous Encaissements : pour les intérêts de retard
  reçus, dividendes encaissés, plus-values, etc. Avant : ces flux étaient
  classés à tort en "Commissions bancaires" (qui mélangeait dépenses
  bancaires et produits financiers).
- "Affacturage / Dailly" sous Encaissements : pour les flux Dailly et BNP
  Paribas Factor. Avant : classés en "Non identifiés" ou "Ventes clients"
  (faussant le calcul du chiffre d'affaires).
- "Dépenses personnelles" sous Autres : pour les virements personnels du
  dirigeant (loyer perso, notes de frais perso, salaire dirigeant via
  compte courant) qui n'étaient ni du salariat ni du flux intergroupe.

Revision ID: h0r1z0n50503
Revises: h0r1z0n50502
Create Date: 2026-05-05 15:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "h0r1z0n50503"
down_revision = "h0r1z0n50502"
branch_labels = None
depends_on = None


NEW_CATS: list[tuple[str, str, str, str]] = [
    # (parent_slug, name, slug, color)
    ("encaissements", "Produits financiers", "produits-financiers", "#16a085"),
    ("encaissements", "Affacturage / Dailly", "affacturage-dailly", "#1abc9c"),
    ("autres", "Dépenses personnelles", "depenses-personnelles", "#e67e22"),
]


def upgrade() -> None:
    conn = op.get_bind()
    for parent_slug, name, slug, color in NEW_CATS:
        parent_id = conn.execute(
            sa.text("SELECT id FROM categories WHERE slug = :s"),
            {"s": parent_slug},
        ).scalar_one_or_none()
        if parent_id is None:
            raise RuntimeError(f"Parent slug '{parent_slug}' introuvable")
        if conn.execute(
            sa.text("SELECT id FROM categories WHERE slug = :s"), {"s": slug}
        ).scalar_one_or_none():
            continue
        conn.execute(
            sa.text(
                "INSERT INTO categories "
                "(name, slug, color, parent_category_id, is_system, created_at) "
                "VALUES (:n, :s, :c, :p, true, NOW())"
            ),
            {"n": name, "s": slug, "c": color, "p": parent_id},
        )


def downgrade() -> None:
    conn = op.get_bind()
    slugs = [s for _, _, s, _ in NEW_CATS]
    conn.execute(
        sa.text("DELETE FROM categories WHERE slug = ANY(:s)"),
        {"s": slugs},
    )
