"""POST /api/rules."""
from fastapi.testclient import TestClient

from app.models.category import Category


def _cat(db_session) -> Category:
    c = Category(name="c", slug="c-api-create", is_system=False)
    db_session.add(c); db_session.commit()
    return c


def test_create_rule_as_reader_forbidden(
    client: TestClient, auth_user_reader, db_session,
) -> None:
    cat = _cat(db_session)
    r = client.post("/api/rules", json={
        "name": "X", "priority": 7000,
        "label_operator": "CONTAINS", "label_value": "X",
        "direction": "ANY", "category_id": cat.id,
    })
    assert r.status_code == 403


def test_create_rule_success(
    client: TestClient, auth_user, db_session,
) -> None:
    cat = _cat(db_session)
    r = client.post("/api/rules", json={
        "name": "Test create",
        "priority": 7100,
        "label_operator": "CONTAINS",
        "label_value": "  urssaf  ",  # sera normalisé
        "direction": "ANY",
        "category_id": cat.id,
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "Test create"
    assert body["label_value"] == "URSSAF"  # normalisé
    assert body["is_system"] is False


def test_create_rule_rejects_empty_filters(
    client: TestClient, auth_user, db_session,
) -> None:
    cat = _cat(db_session)
    r = client.post("/api/rules", json={
        "name": "Empty", "priority": 7200,
        "direction": "ANY", "category_id": cat.id,
    })
    assert r.status_code == 422


def test_create_rule_duplicate_priority_conflict(
    client: TestClient, auth_user, db_session,
) -> None:
    cat = _cat(db_session)
    payload_base = {
        "priority": 7300,
        "label_operator": "CONTAINS", "label_value": "A",
        "direction": "ANY", "category_id": cat.id,
    }
    r1 = client.post("/api/rules", json={**payload_base, "name": "A"})
    assert r1.status_code == 201
    r2 = client.post("/api/rules", json={**payload_base, "name": "B"})
    assert r2.status_code == 409
