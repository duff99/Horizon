"""Matrice de permissions sur /api/rules (reader/admin + entity access)."""
from fastapi.testclient import TestClient

from app.models.category import Category
from app.models.categorization_rule import (
    CategorizationRule,
    RuleDirection,
    RuleLabelOperator,
)
from app.models.entity import Entity


def test_reader_cannot_create(client: TestClient, auth_user_reader, db_session) -> None:
    cat = Category(name="c", slug="c-perm-1", is_system=False)
    db_session.add(cat)
    db_session.commit()

    r = client.post("/api/rules", json={
        "name": "X",
        "priority": 30000,
        "label_operator": "CONTAINS",
        "label_value": "X",
        "direction": "ANY",
        "category_id": cat.id,
    })
    assert r.status_code == 403


def test_reader_cannot_delete(client: TestClient, auth_user_reader, db_session) -> None:
    cat = Category(name="c", slug="c-perm-2", is_system=False)
    db_session.add(cat)
    db_session.commit()

    rule = CategorizationRule(
        name="X",
        priority=30100,
        entity_id=None,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS,
        label_value="X",
        category_id=cat.id,
    )
    db_session.add(rule)
    db_session.commit()

    r = client.delete(f"/api/rules/{rule.id}")
    assert r.status_code == 403


def test_admin_without_entity_access_forbidden(
    client: TestClient, auth_user, db_session,
) -> None:
    other = Entity(name="Hors accès", legal_name="Hors accès SAS")
    db_session.add(other)
    db_session.commit()

    cat = Category(name="c", slug="c-perm-3", is_system=False)
    db_session.add(cat)
    db_session.commit()

    r = client.post("/api/rules", json={
        "name": "No access",
        "priority": 30200,
        "entity_id": other.id,
        "label_operator": "CONTAINS",
        "label_value": "X",
        "direction": "ANY",
        "category_id": cat.id,
    })
    assert r.status_code == 403
