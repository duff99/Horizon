"""F3 — Tests audit events auth : login / login_failed / logout."""
from sqlalchemy import select
from app.models.audit_log import AuditLog


def test_login_success_creates_audit(client, db_session, auth_user_admin):
    """Un login réussi crée une ligne audit action=login."""
    # auth_user_admin est déjà connecté depuis la fixture ; on vérifie la ligne audit.
    rows = db_session.scalars(
        select(AuditLog).where(
            AuditLog.action == "login",
            AuditLog.user_email == auth_user_admin.email,
        )
    ).all()
    assert len(rows) >= 1


def test_login_failed_creates_audit(client, db_session, auth_user_admin):
    """Un login échoué crée une ligne audit action=login_failed."""
    client.post("/api/auth/login", json={
        "email": auth_user_admin.email,
        "password": "WrongPass999!",
    })
    rows = db_session.scalars(
        select(AuditLog).where(
            AuditLog.action == "login_failed",
            AuditLog.user_email == auth_user_admin.email,
        )
    ).all()
    assert len(rows) >= 1


def test_logout_creates_audit(client, db_session, auth_user_admin):
    """Un logout crée une ligne audit action=logout."""
    client.post("/api/auth/logout")
    rows = db_session.scalars(
        select(AuditLog).where(
            AuditLog.action == "logout",
            AuditLog.user_email == auth_user_admin.email,
        )
    ).all()
    assert len(rows) >= 1
