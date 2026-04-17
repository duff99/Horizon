"""Vérifie que la migration B2 a inséré les ~50 sous-catégories."""
from sqlalchemy import select

from app.models.category import Category


EXPECTED_PARENT_SLUGS = {
    "encaissements", "personnel", "charges-sociales", "impots-taxes",
    "charges-externes", "frais-bancaires", "investissements",
    "flux-financiers", "autres",
}


EXPECTED_CHILDREN = {
    "encaissements": {
        "ventes-clients", "subventions-aides",
        "remboursements-encaissements", "autres-encaissements",
    },
    "personnel": {
        "salaires-nets", "acomptes-salaires", "primes-bonus",
        "frais-professionnels-remb",
    },
    "charges-sociales": {
        "urssaf", "retraite", "prevoyance", "mutuelle", "taxe-apprentissage",
        "formation-professionnelle",
    },
    "impots-taxes": {
        "tva-collectee", "tva-deductible", "tva-a-payer",
        "impot-societes", "cfe-cvae", "taxe-fonciere", "autres-taxes",
    },
    "charges-externes": {
        "loyers-charges-locatives", "energie-eau", "telecom-internet",
        "assurances", "honoraires-conseil", "deplacements-missions",
        "fournitures-bureau", "informatique-logiciels",
        "publicite-marketing", "sous-traitance-generique",
    },
    "frais-bancaires": {
        "commissions", "agios-interets", "frais-cartes", "change",
    },
    "investissements": {
        "acquisitions-materiel", "acquisitions-logiciels",
        "acquisitions-immobilier",
    },
    "flux-financiers": {
        "emprunts-remboursements", "apports-comptes-courants",
        "virements-internes", "dividendes-remontees",
    },
    "autres": {
        "non-identifies", "ajustements",
    },
}


def test_all_expected_subcategories_seeded(db_session) -> None:
    for parent_slug, children_slugs in EXPECTED_CHILDREN.items():
        parent = db_session.execute(
            select(Category).where(Category.slug == parent_slug)
        ).scalar_one_or_none()
        assert parent is not None, f"Parent {parent_slug} manquant"
        child_rows = db_session.execute(
            select(Category).where(Category.parent_category_id == parent.id)
        ).scalars().all()
        seeded = {c.slug for c in child_rows}
        missing = children_slugs - seeded
        assert not missing, f"Sous-catégories manquantes sous {parent_slug}: {missing}"


def test_subcategories_are_system(db_session) -> None:
    row = db_session.execute(
        select(Category).where(Category.slug == "urssaf")
    ).scalar_one()
    assert row.is_system is True
