"""E5 — Tests de la page admin client_errors : liste, filtres, acquittement."""
from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.client_error import ClientError
from app.models.user import User


def create_error(
    db_session: Session,
    user_id: int | None = None,
    message: str = "test error",
    severity: str = "error",
) -> ClientError:
    ce = ClientError(
        user_id=user_id,
        severity=severity,
        source="manual",
        message=message,
        occurred_at=datetime.utcnow(),
    )
    db_session.add(ce)
    db_session.commit()
    db_session.refresh(ce)
    return ce


def test_list_client_errors(
    client: TestClient, db_session: Session, auth_user: User
) -> None:
    ce = create_error(db_session, message="kaboom")
    resp = client.get("/api/admin/client-errors")
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["items"]]
    assert ce.id in ids


def test_acknowledge_client_error(
    client: TestClient, db_session: Session, auth_user: User
) -> None:
    ce = create_error(db_session, message="to acknowledge")
    resp = client.patch(f"/api/admin/client-errors/{ce.id}/acknowledge")
    assert resp.status_code == 200
    data = resp.json()
    assert data["acknowledged_at"] is not None

    # Vérifier en DB
    db_session.refresh(ce)
    assert ce.acknowledged_at is not None


def test_filter_acknowledged(
    client: TestClient, db_session: Session, auth_user: User
) -> None:
    ce_open = create_error(db_session, message="open")
    ce_ack = create_error(db_session, message="acked")
    client.patch(f"/api/admin/client-errors/{ce_ack.id}/acknowledge")

    resp = client.get("/api/admin/client-errors?acknowledged=false")
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["items"]]
    assert ce_open.id in ids
    assert ce_ack.id not in ids


def test_filter_acknowledged_true(
    client: TestClient, db_session: Session, auth_user: User
) -> None:
    ce_open = create_error(db_session, message="open2")
    ce_ack = create_error(db_session, message="acked2")
    client.patch(f"/api/admin/client-errors/{ce_ack.id}/acknowledge")

    resp = client.get("/api/admin/client-errors?acknowledged=true")
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["items"]]
    assert ce_ack.id in ids
    assert ce_open.id not in ids


def test_acknowledge_not_found(
    client: TestClient, db_session: Session, auth_user: User
) -> None:
    resp = client.patch("/api/admin/client-errors/999999/acknowledge")
    assert resp.status_code == 404
