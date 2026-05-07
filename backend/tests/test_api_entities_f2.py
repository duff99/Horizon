"""Tests API minimaux — router entities (F2).

Couvre :
- GET    /api/entities          : 200 (admin), 403 (reader)
- POST   /api/entities          : 201 (admin)
- PATCH  /api/entities/{id}     : 200 (admin), 404 (inexistant)
- DELETE /api/entities/{id}     : 204 (admin, entité sans comptes), 409 (comptes rattachés)
"""
from fastapi.testclient import TestClient

from app.models.entity import Entity
from app.models.user import User


# ---------------------------------------------------------------------------
# GET /api/entities
# ---------------------------------------------------------------------------


def test_list_entities_admin(client: TestClient, auth_user_admin: User) -> None:
    """Un admin peut lister les entités."""
    resp = client.get("/api/entities")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_entities_reader_forbidden(client: TestClient, auth_user_reader: User) -> None:
    """Un reader reçoit 403 sur GET /api/entities."""
    resp = client.get("/api/entities")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /api/entities
# ---------------------------------------------------------------------------


def test_create_entity_admin(client: TestClient, auth_user_admin: User) -> None:
    """Un admin peut créer une entité."""
    resp = client.post(
        "/api/entities",
        json={"name": "SAS Test F2", "legal_name": "SAS Test F2 Legal"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "SAS Test F2"


# ---------------------------------------------------------------------------
# PATCH /api/entities/{id}
# ---------------------------------------------------------------------------


def test_update_entity_happy_path(
    client: TestClient, auth_user_admin: User, entity: Entity
) -> None:
    """Un admin peut modifier le nom d'une entité."""
    resp = client.patch(
        f"/api/entities/{entity.id}",
        json={"name": "SAS Renomme F2"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "SAS Renomme F2"


def test_update_entity_not_found(client: TestClient, auth_user_admin: User) -> None:
    """PATCH /api/entities/{id} avec un id inexistant renvoie 404."""
    resp = client.patch("/api/entities/999999", json={"name": "Fantome"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/entities/{id}
# ---------------------------------------------------------------------------


def test_delete_entity_happy_path(
    client: TestClient, auth_user_admin: User, db_session
) -> None:
    """Un admin peut supprimer une entité sans comptes rattachés."""
    from app.models.entity import Entity

    e = Entity(name="SAS A Supprimer F2", legal_name="SAS A Supprimer F2")
    db_session.add(e)
    db_session.commit()
    db_session.refresh(e)

    resp = client.delete(f"/api/entities/{e.id}")
    assert resp.status_code == 204


def test_delete_entity_with_bank_accounts_conflict(
    client: TestClient, auth_user_admin: User, auth_user_with_bank_account: dict
) -> None:
    """Supprimer une entité ayant des comptes bancaires renvoie 409."""
    entity_id = auth_user_with_bank_account["entity"].id
    resp = client.delete(f"/api/entities/{entity_id}")
    assert resp.status_code == 409
