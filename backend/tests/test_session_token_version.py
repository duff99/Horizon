"""Tests C13 : reset MdP admin révoque les sessions actives via session_token_version."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.security import hash_password


def test_password_reset_invalidates_existing_sessions(
    client: TestClient, db_session: Session
) -> None:
    """Après reset MdP du reader par un admin, le cookie reader cesse de fonctionner."""
    # Créer un admin et se logger
    admin = User(
        email="admin-c13@example.com",
        password_hash=hash_password("AdminPwd2026XYZ!"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    reader = User(
        email="reader-c13@example.com",
        password_hash=hash_password("ReaderPwd2026XYZ!"),
        role=UserRole.READER,
        is_active=True,
    )
    db_session.add_all([admin, reader])
    db_session.commit()
    db_session.refresh(admin)
    db_session.refresh(reader)

    # Login admin
    r = client.post(
        "/api/auth/login",
        json={"email": admin.email, "password": "AdminPwd2026XYZ!"},
    )
    assert r.status_code == 200, f"Login admin échoué : {r.text}"
    admin_cookies = dict(client.cookies)

    # Login reader dans un client séparé
    from app.main import app
    from app.db import get_db

    def _override() -> Session:  # type: ignore[return]
        yield db_session

    app.dependency_overrides[get_db] = _override
    reader_client = TestClient(app)
    r = reader_client.post(
        "/api/auth/login",
        json={"email": reader.email, "password": "ReaderPwd2026XYZ!"},
    )
    assert r.status_code == 200, f"Login reader échoué : {r.text}"

    # 1. Le reader fonctionne avant
    r = reader_client.get("/api/me")
    assert r.status_code == 200
    assert r.json()["id"] == reader.id

    # 2. Admin reset le MdP du reader
    # Remettre les cookies admin dans le client principal
    r = client.post(
        f"/api/users/{reader.id}/password",
        json={"new_password": "BrandNewPwd2026XYZ"},
    )
    assert r.status_code == 204, f"Reset MdP échoué : {r.text}"

    # 3. Le cookie du reader devient invalide
    r = reader_client.get("/api/me")
    assert r.status_code == 401, (
        f"Le cookie du reader devrait être révoqué après reset MdP, "
        f"mais a reçu {r.status_code} : {r.text}"
    )


def test_legacy_token_format_decoded_as_v1(client: TestClient, db_session: Session) -> None:
    """Tokens émis avant la migration restent valides en version 1
    tant que User.session_token_version == 1."""
    from itsdangerous import TimestampSigner

    from app.config import get_settings

    settings = get_settings()
    user = User(
        email="legacy@example.com",
        password_hash=hash_password("Legacy2026XYZpwd"),
        role=UserRole.READER,
        is_active=True,
        # session_token_version par défaut = 1
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Token old format = juste l'id signé (sans version)
    signer = TimestampSigner(settings.secret_key)
    legacy_token = signer.sign(str(user.id)).decode("utf-8")
    client.cookies.set("session", legacy_token)
    r = client.get("/api/me")
    assert r.status_code == 200
    assert r.json()["id"] == user.id


def test_new_token_format_includes_version(db_session: Session) -> None:
    """encode_session_token retourne un token qui contient user_id et version."""
    from app.security import decode_session_token, encode_session_token

    token = encode_session_token(user_id=42, version=3, secret="x" * 32)
    user_id, version = decode_session_token(
        token, secret="x" * 32, max_age_seconds=3600
    )
    assert user_id == 42
    assert version == 3


def test_version_mismatch_returns_401(client: TestClient, db_session: Session) -> None:
    """Si session_token_version du token != version en base → 401 Session révoquée."""
    from app.security import encode_session_token
    from app.config import get_settings

    settings = get_settings()
    user = User(
        email="version-mismatch@example.com",
        password_hash=hash_password("SomePwd2026XYZ!"),
        role=UserRole.READER,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Token avec version 1, mais en base on va mettre version 2
    token_v1 = encode_session_token(
        user_id=user.id, version=1, secret=settings.secret_key
    )
    # Bumper la version en base
    user.session_token_version = 2
    db_session.commit()

    client.cookies.set("session", token_v1)
    r = client.get("/api/me")
    assert r.status_code == 401
    assert "révoquée" in r.json()["detail"]
