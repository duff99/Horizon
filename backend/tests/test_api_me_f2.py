"""Tests API minimaux — router me (F2).

Couvre :
- GET  /api/me           : 200 (auth), 401 (non auth)
- POST /api/me/password  : 204 (happy path), 400 (mauvais mot de passe actuel)
"""
from fastapi.testclient import TestClient

from app.models.user import User


def test_me_returns_current_user(client: TestClient, auth_user: User) -> None:
    """GET /api/me renvoie le profil de l'utilisateur connecté."""
    resp = client.get("/api/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == auth_user.email
    assert data["id"] == auth_user.id


def test_me_unauthenticated_returns_401(client: TestClient) -> None:
    """GET /api/me sans cookie de session renvoie 401."""
    resp = client.get("/api/me")
    assert resp.status_code == 401


def test_change_password_happy_path(client: TestClient, auth_user: User) -> None:
    """POST /api/me/password avec le bon mot de passe actuel renvoie 204."""
    resp = client.post(
        "/api/me/password",
        json={
            "current_password": "test-password-123",
            "new_password": "NewPassword456!",
        },
    )
    assert resp.status_code == 204


def test_change_password_wrong_current_returns_400(
    client: TestClient, auth_user: User
) -> None:
    """POST /api/me/password avec le mauvais mot de passe actuel renvoie 400."""
    resp = client.post(
        "/api/me/password",
        json={
            "current_password": "mauvais-mot-de-passe!",
            "new_password": "NewPassword456!",
        },
    )
    assert resp.status_code == 400
