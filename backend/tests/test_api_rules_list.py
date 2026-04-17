"""GET /api/rules — listage avec filtre scope."""
from fastapi.testclient import TestClient

from app.models.categorization_rule import (
    CategorizationRule, RuleLabelOperator, RuleDirection,
)
from app.models.category import Category
from app.models.user_entity_access import UserEntityAccess


def _cat(db_session) -> Category:
    c = Category(name="c", slug="c-api-list", is_system=False)
    db_session.add(c); db_session.commit()
    return c


def test_list_rules_requires_auth(client: TestClient) -> None:
    r = client.get("/api/rules")
    assert r.status_code == 401


def test_list_all_rules(
    client: TestClient, auth_user, db_session, entity,
) -> None:
    # auth_user n'a pas d'accès implicite à l'entité ; on l'ajoute explicitement
    db_session.add(UserEntityAccess(user_id=auth_user.id, entity_id=entity.id))
    cat = _cat(db_session)
    db_session.add(CategorizationRule(
        name="Glob", priority=1500, entity_id=None,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="X",
        category_id=cat.id,
    ))
    db_session.add(CategorizationRule(
        name="Ent", priority=1600, entity_id=entity.id,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="Y",
        category_id=cat.id,
    ))
    db_session.commit()

    r = client.get("/api/rules")
    assert r.status_code == 200
    data = r.json()
    names = {row["name"] for row in data}
    assert {"Glob", "Ent"}.issubset(names)


def test_list_rules_filter_global(
    client: TestClient, auth_user, db_session, entity,
) -> None:
    cat = _cat(db_session)
    db_session.add(CategorizationRule(
        name="G2", priority=1700, entity_id=None,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="Z",
        category_id=cat.id,
    ))
    db_session.add(CategorizationRule(
        name="E2", priority=1800, entity_id=entity.id,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="W",
        category_id=cat.id,
    ))
    db_session.commit()

    r = client.get("/api/rules?scope=global")
    data = r.json()
    names = {row["name"] for row in data}
    assert "G2" in names
    assert "E2" not in names


def test_list_rules_filter_by_entity(
    client: TestClient, auth_user, db_session, entity,
) -> None:
    # auth_user n'a pas d'accès implicite à l'entité ; on l'ajoute explicitement
    db_session.add(UserEntityAccess(user_id=auth_user.id, entity_id=entity.id))
    cat = _cat(db_session)
    db_session.add(CategorizationRule(
        name="ENT1", priority=1900, entity_id=entity.id,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="AA",
        category_id=cat.id,
    ))
    db_session.commit()

    r = client.get(f"/api/rules?entity_id={entity.id}")
    data = r.json()
    names = {row["name"] for row in data}
    assert "ENT1" in names
