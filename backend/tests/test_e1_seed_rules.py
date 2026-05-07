"""E1 — Vérifie que les règles génériques sont présentes après migration."""
from __future__ import annotations

import pytest
from sqlalchemy import select, text

from app.models.categorization_rule import CategorizationRule

EXPECTED_NAMES = [
    "Paiement carte (générique)",
    "Prélèvement Agicap",
    "Prime salariale",
    "Indemnité kilométrique (IK)",
    "Note de frais (remboursement)",
]


def test_e1_rules_exist(db_session):
    for name in EXPECTED_NAMES:
        rule = db_session.execute(
            select(CategorizationRule).where(CategorizationRule.name == name)
        ).scalar_one_or_none()
        assert rule is not None, f"Règle manquante : {name!r}"
        assert rule.is_system is True


def test_e1_migration_idempotent(db_session):
    """Rejouer un INSERT ON CONFLICT DO NOTHING ne crée pas de doublon."""
    count_before = db_session.execute(
        select(CategorizationRule).where(
            CategorizationRule.name == "Paiement carte (générique)"
        )
    ).scalars().all()
    assert len(count_before) >= 1, "La règle doit exister avant ce test"

    # Tenter un INSERT sur la même priorité (scope global = entity_id NULL → COALESCE(NULL,0))
    # ON CONFLICT sur (COALESCE(entity_id,0), priority) → DO NOTHING
    db_session.execute(
        text("""
            INSERT INTO categorization_rules
                (name, priority, is_system, label_operator, label_value, direction,
                 category_id, created_at, updated_at)
            VALUES
                ('Paiement carte (générique)', 4010, true, 'STARTS_WITH', 'CARTE', 'DEBIT',
                 :cat_id, NOW(), NOW())
            ON CONFLICT (COALESCE(entity_id, 0), priority) DO NOTHING
        """),
        {"cat_id": count_before[0].category_id},
    )
    count_after = db_session.execute(
        select(CategorizationRule).where(
            CategorizationRule.name == "Paiement carte (générique)"
        )
    ).scalars().all()
    assert len(count_before) == len(count_after)
