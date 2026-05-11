"""Tests endpoints UserEntityAccess (HIGH-01).

Couvre :
- GET    /api/users/{id}/entity-access          : 200 admin, 403 reader, 404 user
- POST   /api/users/{id}/entity-access          : 201 grant, 409 doublon, 404 entité, 403 reader
- DELETE /api/users/{id}/entity-access/{eid}    : 204 revoke, 404 inconnu, 403 reader
"""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.entity import Entity
from app.models.user import User, UserRole
from app.security import hash_password


def _make_reader(db: Session, email: str = "reader-target@example.com") -> User:
    u = User(
        email=email,
        password_hash=hash_password("placeholder-12345"),
        role=UserRole.READER,
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _make_entity(db: Session, name: str = "SAS Cible") -> Entity:
    e = Entity(name=name, legal_name=name)
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


# ---------------------------------------------------------------------------
# GET
# ---------------------------------------------------------------------------


def test_list_access_empty(
    client: TestClient, db_session: Session, auth_user_admin: User
) -> None:
    target = _make_reader(db_session)
    resp = client.get(f"/api/users/{target.id}/entity-access")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_access_user_not_found(
    client: TestClient, auth_user_admin: User
) -> None:
    resp = client.get("/api/users/999999/entity-access")
    assert resp.status_code == 404


def test_list_access_reader_forbidden(
    client: TestClient, auth_user_reader: User
) -> None:
    resp = client.get(f"/api/users/{auth_user_reader.id}/entity-access")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST (grant)
# ---------------------------------------------------------------------------


def test_grant_happy_path(
    client: TestClient, db_session: Session, auth_user_admin: User
) -> None:
    target = _make_reader(db_session)
    ent = _make_entity(db_session)
    resp = client.post(
        f"/api/users/{target.id}/entity-access",
        json={"entity_id": ent.id},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["user_id"] == target.id
    assert body["entity_id"] == ent.id

    # Vérifie la liste
    resp2 = client.get(f"/api/users/{target.id}/entity-access")
    assert resp2.json() == [ent.id]


def test_grant_duplicate_returns_409(
    client: TestClient, db_session: Session, auth_user_admin: User
) -> None:
    target = _make_reader(db_session)
    ent = _make_entity(db_session)
    r1 = client.post(
        f"/api/users/{target.id}/entity-access", json={"entity_id": ent.id}
    )
    assert r1.status_code == 201
    r2 = client.post(
        f"/api/users/{target.id}/entity-access", json={"entity_id": ent.id}
    )
    assert r2.status_code == 409


def test_grant_user_not_found(
    client: TestClient, db_session: Session, auth_user_admin: User
) -> None:
    ent = _make_entity(db_session)
    resp = client.post(
        "/api/users/999999/entity-access", json={"entity_id": ent.id}
    )
    assert resp.status_code == 404


def test_grant_entity_not_found(
    client: TestClient, db_session: Session, auth_user_admin: User
) -> None:
    target = _make_reader(db_session)
    resp = client.post(
        f"/api/users/{target.id}/entity-access", json={"entity_id": 999999}
    )
    assert resp.status_code == 404


def test_grant_reader_forbidden(
    client: TestClient, auth_user_reader: User
) -> None:
    resp = client.post(
        f"/api/users/{auth_user_reader.id}/entity-access", json={"entity_id": 1}
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# DELETE (revoke)
# ---------------------------------------------------------------------------


def test_revoke_happy_path(
    client: TestClient, db_session: Session, auth_user_admin: User
) -> None:
    target = _make_reader(db_session)
    ent = _make_entity(db_session)
    client.post(f"/api/users/{target.id}/entity-access", json={"entity_id": ent.id})

    resp = client.delete(f"/api/users/{target.id}/entity-access/{ent.id}")
    assert resp.status_code == 204
    resp2 = client.get(f"/api/users/{target.id}/entity-access")
    assert resp2.json() == []


def test_revoke_not_found(
    client: TestClient, db_session: Session, auth_user_admin: User
) -> None:
    target = _make_reader(db_session)
    resp = client.delete(f"/api/users/{target.id}/entity-access/999999")
    assert resp.status_code == 404


def test_revoke_reader_forbidden(
    client: TestClient, auth_user_reader: User
) -> None:
    resp = client.delete(f"/api/users/{auth_user_reader.id}/entity-access/1")
    assert resp.status_code == 403
