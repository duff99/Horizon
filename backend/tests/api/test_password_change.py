"""Tests pour les endpoints de changement de mot de passe (Plan 5a Phase B).

- POST /api/me/password : self-service
- POST /api/users/{id}/password : admin reset
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.user import User


# ---------------------------------------------------------------------------
# POST /api/me/password — self-service
# ---------------------------------------------------------------------------


def test_me_password_happy_path(client: TestClient, auth_user_admin: User) -> None:
    """Admin change son mot de passe puis peut se re-logger avec le nouveau."""
    resp = client.post(
        "/api/me/password",
        json={
            "current_password": "test-password-123",
            "new_password": "new-super-password-456",
        },
    )
    assert resp.status_code == 204, resp.text

    # Logout puis re-login avec le nouveau mot de passe
    client.post("/api/auth/logout")
    client.cookies.clear()
    relog = client.post(
        "/api/auth/login",
        json={
            "email": auth_user_admin.email,
            "password": "new-super-password-456",
        },
    )
    assert relog.status_code == 200, relog.text


def test_me_password_wrong_current(
    client: TestClient, auth_user_admin: User
) -> None:
    """Mot de passe actuel incorrect → 400."""
    resp = client.post(
        "/api/me/password",
        json={
            "current_password": "wrong-current-password",
            "new_password": "new-super-password-456",
        },
    )
    assert resp.status_code == 400
    assert "actuel" in resp.json()["detail"].lower()


def test_me_password_new_too_short(
    client: TestClient, auth_user_admin: User
) -> None:
    """Nouveau mot de passe < 12 caractères → 422 (Pydantic)."""
    resp = client.post(
        "/api/me/password",
        json={
            "current_password": "test-password-123",
            "new_password": "short",
        },
    )
    assert resp.status_code == 422


def test_me_password_bumps_session_token_version(
    client: TestClient, auth_user_admin: User, db_session
) -> None:
    """Changer son mdp doit bumper session_token_version pour révoquer
    les autres sessions actives (cookies volés). La session courante doit
    être réémise pour ne pas auto-déconnecter l'utilisateur.
    """
    initial_version = auth_user_admin.session_token_version

    resp = client.post(
        "/api/me/password",
        json={
            "current_password": "test-password-123",
            "new_password": "new-super-password-456",
        },
    )
    assert resp.status_code == 204, resp.text

    db_session.refresh(auth_user_admin)
    assert auth_user_admin.session_token_version == initial_version + 1, (
        "session_token_version doit être bumpée pour révoquer les cookies volés"
    )

    # Le cookie réémis doit contenir la nouvelle version (sinon l'utilisateur
    # serait déconnecté immédiatement par sa propre action de changement).
    set_cookie_header = resp.headers.get("set-cookie", "")
    assert "session" in set_cookie_header.lower(), (
        "Un nouveau cookie de session doit être réémis"
    )

    # La requête authentifiée suivante doit toujours passer (200 sur /api/me)
    me_resp = client.get("/api/me")
    assert me_resp.status_code == 200, (
        f"Session courante invalidée par son propre changement de mdp : {me_resp.status_code}"
    )


def test_me_password_unauthenticated(client: TestClient) -> None:
    """Sans session → 401."""
    resp = client.post(
        "/api/me/password",
        json={
            "current_password": "whatever",
            "new_password": "new-super-password-456",
        },
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/users/{id}/password — admin reset
# ---------------------------------------------------------------------------


def test_admin_reset_user_password(
    client: TestClient, auth_user_admin: User, db_session
) -> None:
    """Admin reset le mdp d'un reader ; reader peut se logger avec le nouveau."""
    from app.models.user import User, UserRole
    from app.security import hash_password

    reader = User(
        email="reader-target@example.com",
        password_hash=hash_password("original-password-123"),
        role=UserRole.READER,
    )
    db_session.add(reader)
    db_session.commit()
    db_session.refresh(reader)

    resp = client.post(
        f"/api/users/{reader.id}/password",
        json={"new_password": "admin-set-password-789"},
    )
    assert resp.status_code == 204, resp.text

    # Admin logout puis reader login avec le nouveau mdp
    client.post("/api/auth/logout")
    client.cookies.clear()
    relog = client.post(
        "/api/auth/login",
        json={
            "email": reader.email,
            "password": "admin-set-password-789",
        },
    )
    assert relog.status_code == 200, relog.text


def test_non_admin_cannot_reset_password(
    client: TestClient, auth_user_reader: User, db_session
) -> None:
    """Un reader ne peut pas reset le mot de passe d'un autre user → 403."""
    from app.models.user import User, UserRole
    from app.security import hash_password

    other = User(
        email="other-target@example.com",
        password_hash=hash_password("some-password-123"),
        role=UserRole.READER,
    )
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)

    resp = client.post(
        f"/api/users/{other.id}/password",
        json={"new_password": "hacked-password-456"},
    )
    assert resp.status_code == 403


def test_admin_reset_password_user_not_found(
    client: TestClient, auth_user_admin: User
) -> None:
    """Admin reset sur un user_id inexistant → 404."""
    resp = client.post(
        "/api/users/999999/password",
        json={"new_password": "whatever-password-123"},
    )
    assert resp.status_code == 404
