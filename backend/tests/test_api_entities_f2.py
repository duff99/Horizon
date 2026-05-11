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


def test_list_entities_reader_no_grants(
    client: TestClient, auth_user_reader: User,
) -> None:
    """Un reader sans grant reçoit 200 + liste vide (pas 403).

    Le sélecteur d'entité côté frontend appelle GET /api/entities pour
    tous les rôles ; renvoyer 403 le cassait. Le filtrage par accessibilité
    garantit qu'un reader ne voit que ses entités accordées.
    """
    resp = client.get("/api/entities")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_entities_reader_with_grant_filtered(
    client: TestClient,
    auth_user_reader: User,
    db_session,
) -> None:
    """Un reader avec un grant ne voit QUE son entité, pas les autres."""
    from app.models.entity import Entity
    from app.models.user_entity_access import UserEntityAccess

    granted = Entity(name="Reader Granted", legal_name="Reader Granted")
    other = Entity(name="Reader Hidden", legal_name="Reader Hidden")
    db_session.add_all([granted, other])
    db_session.flush()
    db_session.add(
        UserEntityAccess(user_id=auth_user_reader.id, entity_id=granted.id)
    )
    db_session.commit()

    resp = client.get("/api/entities")
    assert resp.status_code == 200
    names = [e["name"] for e in resp.json()]
    assert granted.name in names
    assert other.name not in names, (
        "Le reader voit une entité non grantée → fuite cross-tenant"
    )


def test_create_entity_reader_still_forbidden(
    client: TestClient, auth_user_reader: User,
) -> None:
    """Mutations restent admin-only même si GET est ouvert aux readers."""
    resp = client.post(
        "/api/entities",
        json={"name": "Reader Try Create", "legal_name": "Reader Try Create"},
    )
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
