"""Tests API minimaux — router bootstrap (F2).

Couvre :
- POST /api/bootstrap : 409 quand un admin existe déjà (DB non vide)
- POST /api/bootstrap : 201 quand la DB est vide (testé via un client isolé)
"""
from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import get_db
from app.main import app
from app.models.user import User


def test_bootstrap_rejected_when_admin_exists(
    client: TestClient, auth_user_admin: User
) -> None:
    """Bootstrap doit renvoyer 409 si au moins un utilisateur existe déjà."""
    from app.models.user import User  # import local pour éviter la confusion

    resp = client.post(
        "/api/bootstrap",
        json={
            "email": "newadmin@example.com",
            "password": "SecurePassword123!",
            "role": "admin",
        },
    )
    assert resp.status_code == 409


def test_bootstrap_creates_first_admin_on_empty_db(db_session: Session) -> None:
    """Bootstrap renvoie 201 et crée l'utilisateur quand la DB est vide."""
    def _override() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = _override
    try:
        # La db_session est vide (rollback automatique après chaque test).
        # On n'a pas utilisé auth_user ici, donc aucun user n'existe.
        c = TestClient(app)
        resp = c.post(
            "/api/bootstrap",
            json={
                "email": "firstadmin@example.com",
                "password": "SecurePassword123!",
                "full_name": "Premier Admin",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "firstadmin@example.com"
        assert data["role"] == "admin"
    finally:
        app.dependency_overrides.clear()
