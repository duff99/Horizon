"""Tests API minimaux — router auth (F2).

Couvre :
- POST /api/auth/login   : happy path + 401 mauvais mot de passe
- POST /api/auth/logout  : happy path (204)
"""
from fastapi.testclient import TestClient

from app.models.user import User


def test_login_happy_path(client: TestClient, auth_user: User) -> None:
    """Login avec des identifiants valides renvoie 200 et les infos du user."""
    # auth_user a déjà fait un login dans la fixture ; on en refait un ici
    # avec un client vierge de cookies pour tester la réponse JSON.
    resp = client.post(
        "/api/auth/login",
        json={"email": auth_user.email, "password": "test-password-123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == auth_user.email
    assert data["role"] == auth_user.role.value
    assert "id" in data


def test_login_wrong_password_returns_401(client: TestClient, auth_user: User) -> None:
    """Login avec un mauvais mot de passe renvoie 401."""
    resp = client.post(
        "/api/auth/login",
        json={"email": auth_user.email, "password": "mauvais-mot-de-passe!"},
    )
    assert resp.status_code == 401


def test_login_unknown_email_returns_401(client: TestClient) -> None:
    """Login avec un email inexistant renvoie 401 (pas de 404 pour ne pas révéler l'existence)."""
    resp = client.post(
        "/api/auth/login",
        json={"email": "inconnu@example.com", "password": "test-password-123"},
    )
    assert resp.status_code == 401


def test_logout_happy_path(client: TestClient, auth_user: User) -> None:
    """Logout d'un user connecté renvoie 204."""
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 204
