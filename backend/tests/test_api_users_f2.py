"""Tests API minimaux — router users (F2).

Couvre :
- GET    /api/users             : 200 (admin), 403 (reader)
- POST   /api/users             : 201 (admin), 403 (reader)
- PATCH  /api/users/{id}        : 200 (admin), 404 (inexistant)
- POST   /api/users/{id}/password : 204 (admin), 404 (inexistant)
- DELETE /api/users/{id}        : 204 (admin), 409 (dernier admin)
"""
from fastapi.testclient import TestClient

from app.models.user import User


# ---------------------------------------------------------------------------
# GET /api/users
# ---------------------------------------------------------------------------


def test_list_users_admin(client: TestClient, auth_user_admin: User) -> None:
    """Un admin peut lister tous les utilisateurs."""
    resp = client.get("/api/users")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_users_reader_forbidden(client: TestClient, auth_user_reader: User) -> None:
    """Un reader reçoit 403 sur GET /api/users."""
    resp = client.get("/api/users")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /api/users
# ---------------------------------------------------------------------------


def test_create_user_admin(client: TestClient, auth_user_admin: User) -> None:
    """Un admin peut créer un nouvel utilisateur."""
    resp = client.post(
        "/api/users",
        json={
            "email": "nouveau@example.com",
            "password": "SecurePass123!",
            "role": "reader",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == "nouveau@example.com"


def test_create_user_reader_forbidden(client: TestClient, auth_user_reader: User) -> None:
    """Un reader reçoit 403 sur POST /api/users."""
    resp = client.post(
        "/api/users",
        json={
            "email": "autre@example.com",
            "password": "SecurePass123!",
            "role": "reader",
        },
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /api/users/{id}
# ---------------------------------------------------------------------------


def test_update_user_happy_path(client: TestClient, auth_user_admin: User) -> None:
    """Un admin peut modifier le full_name d'un utilisateur existant."""
    resp = client.patch(
        f"/api/users/{auth_user_admin.id}",
        json={"full_name": "Admin Modifie"},
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Admin Modifie"


def test_update_user_not_found(client: TestClient, auth_user_admin: User) -> None:
    """PATCH /api/users/{id} avec un id inexistant renvoie 404."""
    resp = client.patch("/api/users/999999", json={"full_name": "Fantome"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/users/{id}/password
# ---------------------------------------------------------------------------


def test_reset_user_password_happy_path(
    client: TestClient, auth_user_admin: User
) -> None:
    """Un admin peut réinitialiser le mot de passe d'un utilisateur."""
    resp = client.post(
        f"/api/users/{auth_user_admin.id}/password",
        json={"new_password": "ResetPassword123!"},
    )
    assert resp.status_code == 204


def test_reset_user_password_not_found(
    client: TestClient, auth_user_admin: User
) -> None:
    """POST /api/users/{id}/password avec un id inexistant renvoie 404."""
    resp = client.post(
        "/api/users/999999/password",
        json={"new_password": "ResetPassword123!"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/users/{id}
# ---------------------------------------------------------------------------


def test_deactivate_user_last_admin_conflict(
    client: TestClient, auth_user_admin: User
) -> None:
    """Supprimer le dernier admin actif renvoie 409."""
    resp = client.delete(f"/api/users/{auth_user_admin.id}")
    assert resp.status_code == 409


def test_deactivate_user_happy_path(
    client: TestClient, auth_user_admin: User, db_session
) -> None:
    """Un admin peut désactiver un autre utilisateur."""
    from app.models.user import User, UserRole
    from app.security import hash_password

    # Crée un second utilisateur à désactiver
    other = User(
        email="todeactivate@example.com",
        password_hash=hash_password("test-password-123"),
        role=UserRole.READER,
    )
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)

    resp = client.delete(f"/api/users/{other.id}")
    assert resp.status_code == 204
