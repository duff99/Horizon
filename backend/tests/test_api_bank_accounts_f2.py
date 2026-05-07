"""Tests API minimaux — router bank_accounts (F2).

Couvre :
- GET   /api/bank-accounts        : 200 (tout user auth)
- POST  /api/bank-accounts        : 201 (admin), 403 (reader)
- PATCH /api/bank-accounts/{id}   : 200 (admin), 404 (inexistant)
"""
from fastapi.testclient import TestClient

from app.models.user import User


# ---------------------------------------------------------------------------
# GET /api/bank-accounts
# ---------------------------------------------------------------------------


def test_list_bank_accounts_admin(
    client: TestClient, auth_user_with_bank_account: dict
) -> None:
    """Un admin peut lister les comptes bancaires accessibles."""
    resp = client.get("/api/bank-accounts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_bank_accounts_unauthenticated_returns_401(
    client: TestClient,
) -> None:
    """GET /api/bank-accounts sans session renvoie 401."""
    resp = client.get("/api/bank-accounts")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/bank-accounts
# ---------------------------------------------------------------------------


def test_create_bank_account_admin(
    client: TestClient, auth_user_admin: User, entity: "Entity"
) -> None:
    """Un admin peut créer un compte bancaire."""
    from app.models.entity import Entity  # import local pour éviter l'ambiguité

    resp = client.post(
        "/api/bank-accounts",
        json={
            "entity_id": entity.id,
            "name": "Compte F2 Admin",
            "iban": "FR7630004000031234567890143",
            "bank_name": "BNP Paribas",
            "bank_code": "bnp",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Compte F2 Admin"


def test_create_bank_account_reader_forbidden(
    client: TestClient, auth_user_reader: User, entity: "Entity"
) -> None:
    """Un reader reçoit 403 sur POST /api/bank-accounts."""
    from app.models.entity import Entity  # import local pour éviter l'ambiguité

    resp = client.post(
        "/api/bank-accounts",
        json={
            "entity_id": entity.id,
            "name": "Compte F2 Reader",
            "iban": "FR7630004000031234567890144",
            "bank_name": "BNP Paribas",
            "bank_code": "bnp",
        },
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /api/bank-accounts/{id}
# ---------------------------------------------------------------------------


def test_update_bank_account_happy_path(
    client: TestClient, auth_user_with_bank_account: dict
) -> None:
    """Un admin peut modifier le nom d'un compte bancaire."""
    ba_id = auth_user_with_bank_account["bank_account"].id
    resp = client.patch(
        f"/api/bank-accounts/{ba_id}",
        json={"name": "Compte Renomme F2"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Compte Renomme F2"


def test_update_bank_account_not_found(
    client: TestClient, auth_user_admin: User
) -> None:
    """PATCH /api/bank-accounts/{id} avec un id inexistant renvoie 404."""
    resp = client.patch("/api/bank-accounts/999999", json={"name": "Fantome"})
    assert resp.status_code == 404
