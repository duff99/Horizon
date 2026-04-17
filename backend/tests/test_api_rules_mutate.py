"""PATCH/DELETE sur /api/rules/{id}."""
from fastapi.testclient import TestClient

from app.models.categorization_rule import (
    CategorizationRule, RuleLabelOperator, RuleDirection,
)
from app.models.category import Category


def _rule_setup(db_session) -> tuple[int, int, int]:
    cat = Category(name="c", slug="c-api-mut", is_system=False)
    cat2 = Category(name="c2", slug="c2-api-mut", is_system=False)
    db_session.add_all([cat, cat2]); db_session.commit()
    rule = CategorizationRule(
        name="To edit", priority=8000, entity_id=None,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="XX",
        category_id=cat.id,
    )
    db_session.add(rule); db_session.commit()
    return rule.id, cat.id, cat2.id


def test_patch_rule_updates_fields(
    client: TestClient, auth_user, db_session,
) -> None:
    rid, _, cat2_id = _rule_setup(db_session)
    r = client.patch(f"/api/rules/{rid}", json={
        "name": "Renamed", "category_id": cat2_id,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Renamed"
    assert body["category_id"] == cat2_id


def test_patch_rule_normalizes_label_value(
    client: TestClient, auth_user, db_session,
) -> None:
    rid, *_ = _rule_setup(db_session)
    r = client.patch(f"/api/rules/{rid}", json={"label_value": "  edf "})
    assert r.status_code == 200
    assert r.json()["label_value"] == "EDF"


def test_patch_system_rule_refused_for_structural_fields(
    client: TestClient, auth_user, db_session,
) -> None:
    cat = Category(name="x", slug="x-api-sysedit", is_system=False)
    db_session.add(cat); db_session.commit()
    rule = CategorizationRule(
        name="SYS", priority=8100, entity_id=None, is_system=True,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="SYS",
        category_id=cat.id,
    )
    db_session.add(rule); db_session.commit()

    r_ok = client.patch(f"/api/rules/{rule.id}", json={"name": "SYS Renamed"})
    assert r_ok.status_code == 200
    r_bad = client.patch(f"/api/rules/{rule.id}", json={"label_value": "NEW"})
    assert r_bad.status_code == 409


def test_delete_system_rule_refused(
    client: TestClient, auth_user_admin, db_session,
) -> None:
    cat = Category(name="y", slug="y-api-sysdel", is_system=False)
    db_session.add(cat); db_session.commit()
    rule = CategorizationRule(
        name="SYSDEL", priority=8200, entity_id=None, is_system=True,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="SYS",
        category_id=cat.id,
    )
    db_session.add(rule); db_session.commit()

    r = client.delete(f"/api/rules/{rule.id}")
    assert r.status_code == 409


def test_delete_rule_as_reader_forbidden(
    client: TestClient, auth_user_reader, db_session,
) -> None:
    rid, *_ = _rule_setup(db_session)
    r = client.delete(f"/api/rules/{rid}")
    assert r.status_code == 403


def test_delete_rule_as_admin_success(
    client: TestClient, auth_user_admin, db_session,
) -> None:
    rid, *_ = _rule_setup(db_session)
    r = client.delete(f"/api/rules/{rid}")
    assert r.status_code == 204
