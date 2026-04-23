"""Tests pour /api/admin/audit-log."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.entity import Entity
from app.models.user import User


def _seed_audit(
    db: Session,
    *,
    user: User | None,
    entity_type: str,
    entity_id: str,
    action: str = "update",
    offset_min: int = 0,
) -> AuditLog:
    row = AuditLog(
        user_id=user.id if user is not None else None,
        user_email=user.email if user is not None else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_json={"x": 1},
        after_json={"x": 2},
        diff_json={"x": {"before": 1, "after": 2}},
        occurred_at=datetime.now(UTC) - timedelta(minutes=offset_min),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_admin_audit_requires_auth(client: TestClient) -> None:
    resp = client.get("/api/admin/audit-log")
    assert resp.status_code == 401


def test_admin_audit_forbidden_for_reader(
    client: TestClient, auth_user_reader: User
) -> None:
    resp = client.get("/api/admin/audit-log")
    assert resp.status_code == 403


def test_admin_audit_list_returns_rows(
    client: TestClient, auth_user_admin: User, db_session: Session
) -> None:
    _seed_audit(
        db_session, user=auth_user_admin, entity_type="Entity",
        entity_id="1", action="create", offset_min=60,
    )
    _seed_audit(
        db_session, user=auth_user_admin, entity_type="Entity",
        entity_id="1", action="update", offset_min=10,
    )

    resp = client.get("/api/admin/audit-log")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 2
    # Tri desc occurred_at : update en premier (plus récent)
    assert body["items"][0]["action"] == "update"


def test_admin_audit_filters_by_entity_type(
    client: TestClient, auth_user_admin: User, db_session: Session
) -> None:
    _seed_audit(
        db_session, user=auth_user_admin, entity_type="Entity",
        entity_id="1", action="update",
    )
    _seed_audit(
        db_session, user=auth_user_admin, entity_type="Transaction",
        entity_id="999", action="update",
    )

    resp = client.get("/api/admin/audit-log", params={"entity_type": "Entity"})
    assert resp.status_code == 200
    body = resp.json()
    assert all(item["entity_type"] == "Entity" for item in body["items"])


def test_admin_audit_filters_by_action(
    client: TestClient, auth_user_admin: User, db_session: Session
) -> None:
    _seed_audit(
        db_session, user=auth_user_admin, entity_type="Entity",
        entity_id="1", action="create",
    )
    _seed_audit(
        db_session, user=auth_user_admin, entity_type="Entity",
        entity_id="2", action="delete",
    )

    resp = client.get("/api/admin/audit-log", params={"action": "delete"})
    assert resp.status_code == 200
    body = resp.json()
    assert all(item["action"] == "delete" for item in body["items"])
    assert body["total"] >= 1


def test_admin_audit_pagination(
    client: TestClient, auth_user_admin: User, db_session: Session
) -> None:
    for i in range(5):
        _seed_audit(
            db_session, user=auth_user_admin, entity_type="Entity",
            entity_id=str(i), offset_min=i,
        )

    resp = client.get("/api/admin/audit-log", params={"limit": 2, "offset": 0})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 2
    assert body["limit"] == 2
    assert body["offset"] == 0


def test_e2e_patch_entity_creates_audit_row(
    client: TestClient, auth_user_admin: User, db_session: Session
) -> None:
    """End-to-end : PATCH /api/entities/{id} doit laisser une ligne audit_log."""
    e = Entity(name="E2E Audit Co", legal_name="E2E Audit Co")
    db_session.add(e)
    db_session.commit()
    db_session.refresh(e)

    resp = client.patch(
        f"/api/entities/{e.id}",
        json={"name": "E2E Audit Co Renamed"},
    )
    assert resp.status_code == 200, resp.text

    # Lecture de l'audit log par l'admin
    resp2 = client.get(
        "/api/admin/audit-log",
        params={"entity_type": "Entity", "entity_id": str(e.id)},
    )
    assert resp2.status_code == 200
    body = resp2.json()
    assert body["total"] >= 1
    row = body["items"][0]
    assert row["action"] == "update"
    assert row["entity_type"] == "Entity"
    assert row["entity_id"] == str(e.id)
    assert row["user_id"] == auth_user_admin.id
    assert row["diff_json"] is not None
    assert "name" in row["diff_json"]
    assert row["diff_json"]["name"]["before"] == "E2E Audit Co"
    assert row["diff_json"]["name"]["after"] == "E2E Audit Co Renamed"
