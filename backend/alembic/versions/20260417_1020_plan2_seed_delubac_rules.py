"""Plan 2 B3 : seed ~30 règles système globales pour Delubac / libellés FR standards.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-17 10:20:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


RULES: list[tuple[int, str, str | None, str | None, str, str]] = [
    (1000, "URSSAF",               "CONTAINS",  "URSSAF",            "DEBIT",  "urssaf"),
    (1010, "DGFIP Impôt société",  "CONTAINS",  "DGFIP",             "DEBIT",  "impot-societes"),
    (1020, "TVA (débit)",          "CONTAINS",  "TVA",               "DEBIT",  "tva-a-payer"),
    (1030, "TVA remboursement",    "CONTAINS",  "TVA",               "CREDIT", "tva-a-payer"),
    (1040, "Virement salaire",     "STARTS_WITH","VIR SEPA SALAIRE", "DEBIT",  "salaires-nets"),
    (1050, "Virement acompte",     "CONTAINS",  "ACOMPTE",           "DEBIT",  "acomptes-salaires"),
    (1060, "Prévoyance Humanis",   "CONTAINS",  "HUMANIS",           "DEBIT",  "prevoyance"),
    (1070, "Prévoyance Malakoff",  "CONTAINS",  "MALAKOFF",          "DEBIT",  "prevoyance"),
    (1080, "Mutuelle Alan",        "CONTAINS",  "ALAN",              "DEBIT",  "mutuelle"),
    (1090, "Mutuelle Harmonie",    "CONTAINS",  "HARMONIE MUTUELLE", "DEBIT",  "mutuelle"),
    (1100, "Retraite AG2R",        "CONTAINS",  "AG2R",              "DEBIT",  "retraite"),
    (1110, "Formation pro (OPCO)", "CONTAINS",  "OPCO",              "DEBIT",  "formation-professionnelle"),
    (1120, "EDF",                  "CONTAINS",  "EDF",               "DEBIT",  "energie-eau"),
    (1130, "Engie",                "CONTAINS",  "ENGIE",             "DEBIT",  "energie-eau"),
    (1140, "Eau Veolia",           "CONTAINS",  "VEOLIA",            "DEBIT",  "energie-eau"),
    (1150, "Orange",               "CONTAINS",  "ORANGE",            "DEBIT",  "telecom-internet"),
    (1160, "SFR",                  "CONTAINS",  "SFR",               "DEBIT",  "telecom-internet"),
    (1170, "Free Pro",             "CONTAINS",  "FREE",              "DEBIT",  "telecom-internet"),
    (1180, "AXA assurances",       "CONTAINS",  "AXA",               "DEBIT",  "assurances"),
    (1190, "Allianz",              "CONTAINS",  "ALLIANZ",           "DEBIT",  "assurances"),
    (1200, "Loyer (PRLV SEPA)",    "STARTS_WITH","PRLV SEPA LOYER",  "DEBIT",  "loyers-charges-locatives"),
    (1210, "Google Workspace",     "CONTAINS",  "GOOGLE",            "DEBIT",  "informatique-logiciels"),
    (1220, "Microsoft",            "CONTAINS",  "MICROSOFT",         "DEBIT",  "informatique-logiciels"),
    (1230, "OVH / hébergement",    "CONTAINS",  "OVH",               "DEBIT",  "informatique-logiciels"),
    (1240, "AWS",                  "CONTAINS",  "AMAZON WEB SERVICES","DEBIT", "informatique-logiciels"),
    (1250, "Commission bancaire",  "CONTAINS",  "COMMISSION",        "DEBIT",  "commissions"),
    (1260, "Agios",                "CONTAINS",  "AGIOS",             "DEBIT",  "agios-interets"),
    (1270, "Frais carte",          "CONTAINS",  "COTISATION CARTE",  "DEBIT",  "frais-cartes"),
    (1280, "Virement interne",     "CONTAINS",  "VIREMENT INTERNE",  "ANY",    "virements-internes"),
    (1290, "Dividendes",           "CONTAINS",  "DIVIDENDE",         "ANY",    "dividendes-remontees"),
]


def upgrade() -> None:
    conn = op.get_bind()
    for priority, name, label_op, label_value, direction, cat_slug in RULES:
        cat_id = conn.execute(
            sa.text("SELECT id FROM categories WHERE slug = :s"),
            {"s": cat_slug},
        ).scalar_one_or_none()
        if cat_id is None:
            raise RuntimeError(f"Catégorie '{cat_slug}' introuvable (B2 manquante ?)")

        exists = conn.execute(
            sa.text(
                "SELECT id FROM categorization_rules "
                "WHERE is_system = true AND entity_id IS NULL AND priority = :p"
            ),
            {"p": priority},
        ).scalar_one_or_none()
        if exists:
            continue

        conn.execute(
            sa.text(
                "INSERT INTO categorization_rules "
                "(name, entity_id, priority, is_system, label_operator, label_value, "
                " direction, category_id, created_at, updated_at) "
                "VALUES (:name, NULL, :priority, true, :lop, :lval, :dir, :cat, NOW(), NOW())"
            ),
            {
                "name": name, "priority": priority,
                "lop": label_op, "lval": label_value,
                "dir": direction, "cat": cat_id,
            },
        )


def downgrade() -> None:
    conn = op.get_bind()
    priorities = [p for p, *_ in RULES]
    conn.execute(
        sa.text(
            "DELETE FROM categorization_rules "
            "WHERE is_system = true AND entity_id IS NULL AND priority = ANY(:p)"
        ),
        {"p": priorities},
    )
