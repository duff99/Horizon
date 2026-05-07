"""E1 — Seeding règles génériques manquantes.

Revision ID: h0r1z0ne0100
Revises: h0r1z0nf0600
Create Date: 2026-05-07 20:00:00

Ajoute 11 règles système couvrant les familles Carte, Agicap, Primes/IK/STC,
Notes de frais, Télécom. Idempotent : ON CONFLICT (COALESCE(entity_id,0), priority)
DO NOTHING.

IDs de catégories (vérifiés en prod le 2026-05-07) :
  50 = frais-cartes (Frais sur cartes)
  45 = informatique-logiciels (Informatique & logiciels)
  23 = primes-bonus (Primes & bonus)
  24 = frais-professionnels-remb (Frais pro. remboursés)
  21 = salaires-nets (Salaires nets)
  22 = acomptes-salaires (Acomptes salaires)
  40 = telecom-internet (Télécom & Internet)
"""
from __future__ import annotations

import logging

import sqlalchemy as sa
from alembic import op

logger = logging.getLogger("alembic")

revision = "h0r1z0ne0100"
down_revision = "h0r1z0nf0600"
branch_labels = None
depends_on = None

# IDs de catégories vérifiés en prod 2026-05-07
CAT_CARTE = 50   # Frais sur cartes
CAT_SAAS = 45    # Informatique & logiciels
CAT_PRIMES = 23  # Primes & bonus
CAT_NDF = 24     # Frais pro. remboursés
CAT_SALAIRES = 21  # Salaires nets
CAT_ACOMPTES = 22  # Acomptes salaires
CAT_TELCO = 40   # Télécom & Internet

RULES = [
    # (name, priority, label_operator, label_value, direction, category_id)
    ("Paiement carte (générique)",          4010, "STARTS_WITH", "CARTE",                 "DEBIT", CAT_CARTE),
    ("Prélèvement Agicap",                  4020, "CONTAINS",    "AGICAP",                "ANY",   CAT_SAAS),
    ("Prime salariale",                     4030, "CONTAINS",    "PRIME",                 "DEBIT", CAT_PRIMES),
    ("Indemnité kilométrique (IK)",         4031, "CONTAINS",    "INDEMNITE KILOMETRIQUE", "DEBIT", CAT_NDF),
    ("Indemnité kilométrique (abrév.)",     4032, "CONTAINS",    "IK",                    "DEBIT", CAT_NDF),
    ("Solde de tout compte",               4033, "CONTAINS",    "SOLDE DE TOUT COMPTE",  "DEBIT", CAT_SALAIRES),
    ("Acompte salarié",                    4034, "CONTAINS",    "ACOMPTE",               "DEBIT", CAT_ACOMPTES),
    ("Note de frais (remboursement)",      4040, "CONTAINS",    "NOTE DE FRAIS",         "DEBIT", CAT_NDF),
    ("Abonnement télécom (générique)",     4062, "CONTAINS",    "ABONNEMENT TEL",        "DEBIT", CAT_TELCO),
    ("Remboursement frais pro",            4041, "CONTAINS",    "REMBOURSEMENT FRAIS",   "DEBIT", CAT_NDF),
    ("Virement IK (abrév. inline)",        4035, "CONTAINS",    "VIR IK",                "DEBIT", CAT_NDF),
]


def upgrade() -> None:
    bind = op.get_bind()
    # Vérifier quelles catégories existent réellement
    cat_ids = {row[0] for row in bind.execute(sa.text("SELECT id FROM categories")).fetchall()}
    for (name, priority, lop, lval, direction, cat_id) in RULES:
        if cat_id not in cat_ids:
            logger.warning("E1 seed: catégorie id=%s introuvable, règle '%s' ignorée.", cat_id, name)
            continue
        bind.execute(
            sa.text("""
                INSERT INTO categorization_rules
                    (name, priority, is_system, label_operator, label_value,
                     direction, category_id, created_at, updated_at)
                VALUES
                    (:name, :priority, true, :lop, :lval,
                     :direction, :cat_id, NOW(), NOW())
                ON CONFLICT (COALESCE(entity_id, 0), priority) DO NOTHING
            """),
            {
                "name": name,
                "priority": priority,
                "lop": lop,
                "lval": lval,
                "direction": direction,
                "cat_id": cat_id,
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    names = [r[0] for r in RULES]
    bind.execute(
        sa.text(
            "DELETE FROM categorization_rules WHERE name = ANY(:names) AND is_system = true"
        ),
        {"names": names},
    )
