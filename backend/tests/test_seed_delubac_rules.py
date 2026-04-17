"""Vérifie la migration B3 : ~30 règles système globales."""
from sqlalchemy import select, func

from app.models.categorization_rule import CategorizationRule


def test_seeded_rules_count(db_session) -> None:
    count = db_session.execute(
        select(func.count(CategorizationRule.id)).where(
            CategorizationRule.is_system.is_(True),
            CategorizationRule.entity_id.is_(None),
        )
    ).scalar_one()
    assert count >= 28, f"{count} règles système seed (attendu >= 28)"


def test_seeded_priorities_unique(db_session) -> None:
    rows = db_session.execute(
        select(CategorizationRule.priority).where(
            CategorizationRule.is_system.is_(True),
            CategorizationRule.entity_id.is_(None),
        )
    ).scalars().all()
    assert len(rows) == len(set(rows)), "Priorités système dupliquées"


def test_urssaf_rule_exists(db_session) -> None:
    r = db_session.execute(
        select(CategorizationRule).where(
            CategorizationRule.is_system.is_(True),
            CategorizationRule.label_value == "URSSAF",
        )
    ).scalar_one_or_none()
    assert r is not None
    assert r.category_id is not None


def test_all_seeded_categories_exist(db_session) -> None:
    from app.models.category import Category
    rules = db_session.execute(
        select(CategorizationRule).where(CategorizationRule.is_system.is_(True))
    ).scalars().all()
    for rule in rules:
        cat = db_session.get(Category, rule.category_id)
        assert cat is not None, f"Règle {rule.name} pointe vers catégorie inexistante"
