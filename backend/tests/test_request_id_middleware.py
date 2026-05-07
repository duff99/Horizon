"""Tests du middleware X-Request-ID.

Vérifie :
1. Un request-id est généré automatiquement si le header est absent.
2. Le header fourni par le client est renvoyé tel quel (propagation).
3. L'audit_log enregistre le request-id quand il est fourni par le client.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def test_request_id_generated_when_absent(client: TestClient) -> None:
    r = client.get("/api/healthz")
    assert "x-request-id" in r.headers
    assert len(r.headers["x-request-id"]) >= 16


def test_request_id_propagated_when_provided(client: TestClient) -> None:
    r = client.get("/api/healthz", headers={"X-Request-ID": "abc-123"})
    assert r.headers["x-request-id"] == "abc-123"


def test_request_id_recorded_in_audit_log(
    client: TestClient,
    auth_user_admin,
    db_session: Session,
) -> None:
    """Quand un admin envoie X-Request-ID, l'audit_log le conserve."""
    from sqlalchemy import select

    from app.models.audit_log import AuditLog

    rid = "test-rid-789"
    r = client.post(
        "/api/users",
        json={
            "email": "rid-test@example.com",
            "password": "Foobar2026XYZ!",
            "role": "reader",
            "full_name": "rid test",
        },
        headers={"X-Request-ID": rid},
    )
    assert r.status_code == 201, r.text

    last = db_session.execute(
        select(AuditLog).order_by(AuditLog.id.desc()).limit(1)
    ).scalar_one()
    assert last.request_id == rid
