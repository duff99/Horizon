"""Tests pour les endpoints client-errors (POST anonyme + GET admin)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.client_error import ClientError
from app.models.user import User


# ---------------------------------------------------------------------------
# POST /api/client-errors — auth optionnelle
# ---------------------------------------------------------------------------


def test_post_client_error_anonymous(client: TestClient, db_session: Session) -> None:
    """Sans cookie, l'erreur est insérée avec user_id NULL."""
    r = client.post(
        "/api/client-errors",
        json={
            "severity": "error",
            "source": "window.onerror",
            "message": "Cannot read property 'foo' of undefined",
            "url": "https://horizon.acreedconsulting.com/analyse",
        },
    )
    assert r.status_code == 204, r.text
    rows = db_session.query(ClientError).all()
    assert len(rows) == 1
    assert rows[0].user_id is None
    assert rows[0].source == "window.onerror"
    assert rows[0].severity == "error"


def test_post_client_error_authenticated(
    client: TestClient, auth_user: User, db_session: Session
) -> None:
    """Avec cookie valide, l'erreur est associée au user."""
    r = client.post(
        "/api/client-errors",
        json={
            "severity": "warning",
            "source": "apifetch",
            "message": "GET /api/analysis/runway 422",
            "request_id": "req-abc-123",
        },
    )
    assert r.status_code == 204
    rows = db_session.query(ClientError).all()
    assert len(rows) == 1
    assert rows[0].user_id == auth_user.id


def test_post_client_error_rejects_invalid_source(client: TestClient) -> None:
    r = client.post(
        "/api/client-errors",
        json={"source": "not-a-valid-source", "message": "x"},
    )
    assert r.status_code == 422


def test_post_client_error_rejects_invalid_severity(client: TestClient) -> None:
    r = client.post(
        "/api/client-errors",
        json={
            "severity": "panic",
            "source": "manual",
            "message": "x",
        },
    )
    assert r.status_code == 422


def test_post_client_error_message_required(client: TestClient) -> None:
    r = client.post(
        "/api/client-errors",
        json={"source": "manual", "message": ""},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/admin/client-errors — admin only, filtres, pagination
# ---------------------------------------------------------------------------


def test_admin_list_requires_admin(
    client: TestClient, auth_user_reader: User
) -> None:
    r = client.get("/api/admin/client-errors")
    assert r.status_code == 403


def test_admin_list_returns_recent_first(
    client: TestClient, auth_user: User, db_session: Session
) -> None:
    # Insert via DB direct (le POST rate-limited n'est pas le sujet ici)
    now = datetime.now(UTC)
    older = ClientError(
        user_id=None,
        source="window.onerror",
        severity="error",
        message="old",
        occurred_at=now - timedelta(hours=2),
    )
    newer = ClientError(
        user_id=None,
        source="apifetch",
        severity="warning",
        message="new",
        occurred_at=now,
    )
    db_session.add_all([older, newer])
    db_session.commit()

    r = client.get("/api/admin/client-errors")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert body["items"][0]["message"] == "new"
    assert body["items"][1]["message"] == "old"


def test_admin_list_filters_by_severity(
    client: TestClient, auth_user: User, db_session: Session
) -> None:
    db_session.add_all(
        [
            ClientError(source="manual", severity="error", message="e1"),
            ClientError(source="manual", severity="warning", message="w1"),
            ClientError(source="manual", severity="error", message="e2"),
        ]
    )
    db_session.commit()

    r = client.get("/api/admin/client-errors?severity=error")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert all(it["severity"] == "error" for it in body["items"])


def test_admin_list_pagination(
    client: TestClient, auth_user: User, db_session: Session
) -> None:
    db_session.add_all(
        [
            ClientError(source="manual", severity="error", message=f"m{i}")
            for i in range(5)
        ]
    )
    db_session.commit()

    r = client.get("/api/admin/client-errors?limit=2&offset=0")
    body = r.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2

    r = client.get("/api/admin/client-errors?limit=2&offset=4")
    body = r.json()
    assert len(body["items"]) == 1


def test_admin_list_includes_user_email_when_user_set(
    client: TestClient, auth_user: User, db_session: Session
) -> None:
    db_session.add(
        ClientError(
            user_id=auth_user.id, source="apifetch", severity="error", message="x"
        )
    )
    db_session.commit()

    r = client.get("/api/admin/client-errors")
    body = r.json()
    assert body["items"][0]["user_email"] == auth_user.email
