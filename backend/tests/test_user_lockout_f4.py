"""F4 — Tests lockout après 5 échecs de connexion."""
from datetime import UTC, datetime

from sqlalchemy import select

from app.models.user import User


def _fail_login(client, email: str, n: int) -> None:
    for _ in range(n):
        client.post("/api/auth/login", json={
            "email": email,
            "password": "WrongPass999!",
        })


def test_lockout_after_5_failures(client, db_session, auth_user_admin):
    """6e tentative (mot de passe incorrect) après 5 échecs → 423."""
    _fail_login(client, auth_user_admin.email, 5)
    resp = client.post("/api/auth/login", json={
        "email": auth_user_admin.email,
        "password": "WrongPass999!",
    })
    assert resp.status_code == 423


def test_correct_password_rejected_while_locked(client, db_session, auth_user_admin):
    """Même le bon mot de passe est rejeté si le compte est verrouillé."""
    _fail_login(client, auth_user_admin.email, 5)
    resp = client.post("/api/auth/login", json={
        "email": auth_user_admin.email,
        "password": "test-password-123",
    })
    assert resp.status_code == 423


def test_counter_reset_on_success(client, db_session, auth_user_admin):
    """4 échecs + 1 succès → compteur remis à 0, pas de lockout."""
    _fail_login(client, auth_user_admin.email, 4)
    # Login réussi
    resp = client.post("/api/auth/login", json={
        "email": auth_user_admin.email,
        "password": "test-password-123",
    })
    assert resp.status_code == 200
    # Vérifier que le compteur est à 0
    db_session.expire(auth_user_admin)
    user = db_session.get(User, auth_user_admin.id)
    assert user.failed_login_attempts == 0
    assert user.locked_until is None


def test_locked_until_set_after_5_failures(client, db_session, auth_user_admin):
    """Après 5 échecs, locked_until est dans le futur."""
    _fail_login(client, auth_user_admin.email, 5)
    db_session.expire(auth_user_admin)
    user = db_session.get(User, auth_user_admin.id)
    assert user.locked_until is not None
    assert user.locked_until > datetime.now(UTC)


def test_lockout_message_does_not_reveal_attempt_count(client, db_session, auth_user_admin):
    """Le message 423 ne révèle pas combien d'échecs il reste avant lockout."""
    _fail_login(client, auth_user_admin.email, 5)
    resp = client.post("/api/auth/login", json={
        "email": auth_user_admin.email,
        "password": "WrongPass999!",
    })
    assert resp.status_code == 423
    detail = resp.json().get("detail", "")
    # Le message ne doit pas contenir de chiffre indiquant les tentatives restantes
    assert "tentatives restantes" not in detail.lower()
    assert "reste" not in detail.lower()
    assert "verrouillé" in detail.lower()
