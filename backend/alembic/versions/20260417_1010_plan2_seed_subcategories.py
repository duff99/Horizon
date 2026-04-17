"""Plan 2 B2 : seed ~50 sous-catégories sous les 9 racines.

Note d'écart : Plan 1 a seedé des slugs racines différents de ceux attendus
par Plan 2 (ex. `decaissements-personnel` vs `personnel`). Cette migration
crée donc d'abord les racines manquantes (idempotent via vérif slug) avant
d'insérer les sous-catégories.

Schéma actuel (cf. app/models/category.py) : la table `categories` a les
colonnes (name, slug, color, parent_category_id, is_system, created_at).
Il n'y a PAS de colonne `updated_at`.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-17 10:10:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


# Racines attendues par Plan 2 : (slug, name, color)
EXPECTED_ROOTS: list[tuple[str, str, str]] = [
    ("encaissements", "Encaissements", "#2ecc71"),
    ("personnel", "Personnel", "#e74c3c"),
    ("charges-sociales", "Charges sociales", "#9b59b6"),
    ("impots-taxes", "Impôts & taxes", "#f39c12"),
    ("charges-externes", "Charges externes", "#3498db"),
    ("frais-bancaires", "Frais bancaires", "#7f8c8d"),
    ("investissements", "Investissements", "#34495e"),
    ("flux-financiers", "Flux financiers", "#16a085"),
    ("autres", "Autres", "#b2babb"),
]


SUBCATS: dict[str, list[tuple[str, str, str | None]]] = {
    "encaissements": [
        ("Ventes clients", "ventes-clients", "#2ecc71"),
        ("Subventions & aides", "subventions-aides", "#27ae60"),
        ("Remboursements reçus", "remboursements-encaissements", "#16a085"),
        ("Autres encaissements", "autres-encaissements", "#1abc9c"),
    ],
    "personnel": [
        ("Salaires nets", "salaires-nets", "#e74c3c"),
        ("Acomptes salaires", "acomptes-salaires", "#c0392b"),
        ("Primes & bonus", "primes-bonus", "#d35400"),
        ("Frais pro. remboursés", "frais-professionnels-remb", "#e67e22"),
    ],
    "charges-sociales": [
        ("URSSAF", "urssaf", "#9b59b6"),
        ("Retraite", "retraite", "#8e44ad"),
        ("Prévoyance", "prevoyance", "#8e44ad"),
        ("Mutuelle", "mutuelle", "#8e44ad"),
        ("Taxe d'apprentissage", "taxe-apprentissage", "#8e44ad"),
        ("Formation professionnelle", "formation-professionnelle", "#8e44ad"),
    ],
    "impots-taxes": [
        ("TVA collectée", "tva-collectee", "#f39c12"),
        ("TVA déductible", "tva-deductible", "#f1c40f"),
        ("TVA à payer/rembourser", "tva-a-payer", "#e67e22"),
        ("Impôt sur les sociétés", "impot-societes", "#d35400"),
        ("CFE / CVAE", "cfe-cvae", "#c0392b"),
        ("Taxe foncière", "taxe-fonciere", "#a0522d"),
        ("Autres taxes", "autres-taxes", "#95a5a6"),
    ],
    "charges-externes": [
        ("Loyers & charges locatives", "loyers-charges-locatives", "#3498db"),
        ("Énergie & eau", "energie-eau", "#2980b9"),
        ("Télécom & Internet", "telecom-internet", "#5dade2"),
        ("Assurances", "assurances", "#85c1e9"),
        ("Honoraires & conseil", "honoraires-conseil", "#2874a6"),
        ("Déplacements & missions", "deplacements-missions", "#1f618d"),
        ("Fournitures de bureau", "fournitures-bureau", "#aed6f1"),
        ("Informatique & logiciels", "informatique-logiciels", "#5499c7"),
        ("Publicité & marketing", "publicite-marketing", "#2e86c1"),
        ("Sous-traitance (générique)", "sous-traitance-generique", "#154360"),
    ],
    "frais-bancaires": [
        ("Commissions bancaires", "commissions", "#7f8c8d"),
        ("Agios & intérêts", "agios-interets", "#95a5a6"),
        ("Frais sur cartes", "frais-cartes", "#bdc3c7"),
        ("Opérations de change", "change", "#7f8c8d"),
    ],
    "investissements": [
        ("Acquisitions matériel", "acquisitions-materiel", "#34495e"),
        ("Acquisitions logiciels", "acquisitions-logiciels", "#2c3e50"),
        ("Acquisitions immobilier", "acquisitions-immobilier", "#1c2833"),
    ],
    "flux-financiers": [
        ("Emprunts & remboursements", "emprunts-remboursements", "#16a085"),
        ("Apports & comptes courants", "apports-comptes-courants", "#1abc9c"),
        ("Virements internes", "virements-internes", "#48c9b0"),
        ("Dividendes & remontées", "dividendes-remontees", "#117864"),
    ],
    "autres": [
        ("Non identifiés", "non-identifies", "#b2babb"),
        ("Ajustements", "ajustements", "#d5dbdb"),
    ],
}


def upgrade() -> None:
    conn = op.get_bind()

    # 1) Créer les racines manquantes (idempotent).
    for slug, name, color in EXPECTED_ROOTS:
        exists = conn.execute(
            sa.text("SELECT id FROM categories WHERE slug = :s"),
            {"s": slug},
        ).scalar_one_or_none()
        if exists:
            continue
        conn.execute(
            sa.text(
                "INSERT INTO categories "
                "(name, slug, color, parent_category_id, is_system, created_at) "
                "VALUES (:name, :slug, :color, NULL, true, NOW())"
            ),
            {"name": name, "slug": slug, "color": color},
        )

    # 2) Insérer les sous-catégories sous chaque racine attendue.
    for parent_slug, children in SUBCATS.items():
        parent_id = conn.execute(
            sa.text("SELECT id FROM categories WHERE slug = :s"),
            {"s": parent_slug},
        ).scalar_one()

        for name, slug, color in children:
            exists = conn.execute(
                sa.text("SELECT id FROM categories WHERE slug = :s"),
                {"s": slug},
            ).scalar_one_or_none()
            if exists:
                continue
            conn.execute(
                sa.text(
                    "INSERT INTO categories "
                    "(name, slug, color, parent_category_id, is_system, created_at) "
                    "VALUES (:name, :slug, :color, :parent, true, NOW())"
                ),
                {"name": name, "slug": slug, "color": color, "parent": parent_id},
            )


def downgrade() -> None:
    conn = op.get_bind()
    # Supprimer les sous-catégories (les racines créées ici ne sont PAS
    # supprimées : elles peuvent être référencées par des règles seed B3
    # ou avoir été créées dans une autre migration).
    slugs = [slug for children in SUBCATS.values() for _, slug, _ in children]
    conn.execute(
        sa.text("DELETE FROM categories WHERE slug = ANY(:slugs)"),
        {"slugs": slugs},
    )
