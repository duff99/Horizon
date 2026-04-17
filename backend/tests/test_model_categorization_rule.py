"""Tests du modèle CategorizationRule."""
import pytest
from decimal import Decimal
from sqlalchemy.exc import IntegrityError

from app.models.categorization_rule import (
    CategorizationRule,
    RuleLabelOperator,
    RuleAmountOperator,
    RuleDirection,
)
from app.models.category import Category
from app.models.entity import Entity


def _mk_category(db_session) -> Category:
    c = Category(name="Test cat", slug="test-cat-rule", is_system=False)
    db_session.add(c)
    db_session.commit()
    return c


def test_rule_basic_fields(db_session) -> None:
    cat = _mk_category(db_session)
    rule = CategorizationRule(
        name="URSSAF test",
        entity_id=None,
        priority=1000,
        is_system=False,
        label_operator=RuleLabelOperator.CONTAINS,
        label_value="URSSAF",
        direction=RuleDirection.ANY,
        category_id=cat.id,
    )
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)
    assert rule.id is not None
    assert rule.created_at is not None
    assert rule.direction == RuleDirection.ANY


def test_rule_priority_unique_per_scope(db_session) -> None:
    cat = _mk_category(db_session)
    db_session.add(CategorizationRule(
        name="A", priority=500, direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="A",
        category_id=cat.id,
    ))
    db_session.commit()
    db_session.add(CategorizationRule(
        name="B", priority=500, direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="B",
        category_id=cat.id,
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_rule_same_priority_different_entity_ok(
    db_session, entity: Entity
) -> None:
    cat = _mk_category(db_session)
    db_session.add(CategorizationRule(
        name="Global", priority=500, entity_id=None,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="X",
        category_id=cat.id,
    ))
    db_session.add(CategorizationRule(
        name="Entity", priority=500, entity_id=entity.id,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="X",
        category_id=cat.id,
    ))
    db_session.commit()  # doit passer — scopes différents


def test_rule_amount_between_requires_both_values(db_session) -> None:
    cat = _mk_category(db_session)
    rule = CategorizationRule(
        name="Bad between", priority=600,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="X",
        amount_operator=RuleAmountOperator.BETWEEN,
        amount_value=Decimal("100"),
        amount_value2=None,
        category_id=cat.id,
    )
    db_session.add(rule)
    with pytest.raises(IntegrityError):
        db_session.commit()
