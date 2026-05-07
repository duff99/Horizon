"""D2 — Ajoute Category.kind (in/out/both) + seeding des catégories existantes.

Revision ID: h0r1z0n50802
Revises: h0r1z0n50801
Create Date: 2026-05-08 10:10:00
"""
from __future__ import annotations
import sqlalchemy as sa
from alembic import op

revision = "h0r1z0n50802"
down_revision = "h0r1z0n50801"
branch_labels = None
depends_on = None

IN_SLUGS = [
    "encaissements", "ventes-clients", "subventions-aides",
    "remboursements-encaissements", "autres-encaissements",
    "produits-financiers", "affacturage-dailly",
]
OUT_SLUGS = [
    "decaissements-personnel", "decaissements-sous-traitants",
    "decaissements-fournisseurs", "personnel", "charges-sociales",
    "charges-externes", "frais-bancaires", "investissements",
    "honoraires-juridiques",
    "salaires-nets", "acomptes-salaires", "primes-bonus",
    "frais-professionnels-remb",
    "urssaf", "retraite", "prevoyance", "mutuelle",
    "taxe-apprentissage", "formation-professionnelle",
    "loyers-charges-locatives", "energie-eau", "telecom-internet",
    "assurances", "honoraires-conseil", "deplacements-missions",
    "fournitures-bureau", "informatique-logiciels",
    "publicite-marketing", "sous-traitance-generique",
    "commissions", "agios-interets", "frais-cartes", "change",
    "acquisitions-materiel", "acquisitions-logiciels",
    "acquisitions-immobilier",
]
BOTH_SLUGS = [
    "impots-taxes", "flux-financiers", "flux-intergroupe",
    "autres", "non-categorisees",
    "tva-collectee", "tva-deductible", "tva-a-payer",
    "impot-societes", "cfe-cvae", "taxe-fonciere", "autres-taxes",
    "emprunts-remboursements", "apports-comptes-courants",
    "virements-internes", "dividendes-remontees",
    "non-identifies", "ajustements", "depenses-personnelles",
    "charges-sociales-taxes",
]


def upgrade() -> None:
    conn = op.get_bind()
    op.add_column(
        "categories",
        sa.Column("kind", sa.String(4), nullable=False, server_default="both"),
    )
    conn.execute(
        sa.text("UPDATE categories SET kind='in' WHERE slug = ANY(:s)"),
        {"s": IN_SLUGS},
    )
    conn.execute(
        sa.text("UPDATE categories SET kind='out' WHERE slug = ANY(:s)"),
        {"s": OUT_SLUGS},
    )
    conn.execute(
        sa.text("UPDATE categories SET kind='both' WHERE slug = ANY(:s)"),
        {"s": BOTH_SLUGS},
    )


def downgrade() -> None:
    op.drop_column("categories", "kind")
