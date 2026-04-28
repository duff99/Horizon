"""Tests pour les endpoints /api/admin/backups (list, disk, trigger)."""
from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.backup_history import BackupHistory
from app.models.user import User


def _seed_backup(
    db: Session,
    *,
    status: str,
    file_path: str,
    offset_min: int = 0,
    type: str = "scheduled",
) -> BackupHistory:
    row = BackupHistory(
        status=status,
        type=type,
        file_path=file_path,
        started_at=datetime.now(UTC) - timedelta(minutes=offset_min),
        size_bytes=1234,
        sha256="a" * 64,
        imports_size_bytes=4321,
        imports_sha256="b" * 64,
        row_counts_json={"users": 1, "transactions": 42},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_admin_backups_requires_auth(client: TestClient) -> None:
    resp = client.get("/api/admin/backups")
    assert resp.status_code == 401


def test_admin_backups_forbidden_for_reader(
    client: TestClient, auth_user_reader: User
) -> None:
    resp = client.get("/api/admin/backups")
    assert resp.status_code == 403


def test_admin_backups_returns_rows_ordered(
    client: TestClient, auth_user_admin: User, db_session: Session
) -> None:
    _seed_backup(
        db_session,
        status="success",
        file_path="./backups/horizon-oldest.dump",
        offset_min=60,
    )
    _seed_backup(
        db_session,
        status="failed",
        file_path="./backups/horizon-mid.dump",
        offset_min=30,
    )
    _seed_backup(
        db_session,
        status="success",
        file_path="./backups/horizon-newest.dump",
        offset_min=0,
    )

    resp = client.get("/api/admin/backups")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 3
    # Le plus récent en premier
    assert body[0]["file_path"].endswith("newest.dump")
    assert body[-1]["file_path"].endswith("oldest.dump")
    # Vérifie les champs exposés
    first = body[0]
    assert first["status"] == "success"
    assert first["type"] == "scheduled"
    assert first["size_bytes"] == 1234
    assert first["imports_size_bytes"] == 4321
    assert first["row_counts_json"] == {"users": 1, "transactions": 42}


# ---------------------------------------------------------------------------
# GET /api/admin/backups/disk
# ---------------------------------------------------------------------------


def test_admin_backups_disk_returns_stats(
    client: TestClient, auth_user_admin: User
) -> None:
    resp = client.get("/api/admin/backups/disk")
    assert resp.status_code == 200
    body = resp.json()
    assert body["mount"] == "/"
    assert body["size_gb"] > 0
    assert 0 <= body["used_pct"] <= 100
    assert body["status"] in ("ok", "alert")


def test_admin_backups_disk_forbidden_for_reader(
    client: TestClient, auth_user_reader: User
) -> None:
    resp = client.get("/api/admin/backups/disk")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /api/admin/backups/trigger
# ---------------------------------------------------------------------------


@pytest.fixture
def trigger_dir(tmp_path, monkeypatch):
    """Override le dossier triggers vers un tmp local pour les tests."""
    d = tmp_path / "triggers"
    d.mkdir()
    monkeypatch.setattr("app.api.admin_backups._TRIGGER_DIR", str(d))
    return d


def test_trigger_creates_pending_row_and_writes_file(
    client: TestClient,
    auth_user_admin: User,
    db_session: Session,
    trigger_dir,
) -> None:
    resp = client.post(
        "/api/admin/backups/trigger", json={"type": "manual"}
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    row_id = body["row_id"]

    # Row pending en DB
    row = db_session.query(BackupHistory).filter_by(id=row_id).one()
    assert row.status == "pending"
    assert row.type == "manual"

    # Fichier trigger écrit
    files = list(trigger_dir.iterdir())
    assert len(files) == 1
    assert files[0].name == f"{row_id}.json"
    content = files[0].read_text()
    assert row_id in content
    assert "manual" in content


def test_trigger_accepts_restore_test(
    client: TestClient,
    auth_user_admin: User,
    db_session: Session,
    trigger_dir,
) -> None:
    resp = client.post(
        "/api/admin/backups/trigger", json={"type": "restore-test"}
    )
    assert resp.status_code == 201
    row_id = resp.json()["row_id"]
    row = db_session.query(BackupHistory).filter_by(id=row_id).one()
    assert row.type == "restore-test"


def test_trigger_rejects_invalid_type(
    client: TestClient, auth_user_admin: User, trigger_dir
) -> None:
    resp = client.post(
        "/api/admin/backups/trigger", json={"type": "scheduled"}
    )
    assert resp.status_code == 400


def test_trigger_blocks_if_pending_in_flight(
    client: TestClient,
    auth_user_admin: User,
    db_session: Session,
    trigger_dir,
) -> None:
    _seed_backup(
        db_session,
        status="pending",
        file_path="pending",
        type="manual",
    )
    resp = client.post(
        "/api/admin/backups/trigger", json={"type": "manual"}
    )
    assert resp.status_code == 409


def test_trigger_blocks_if_running_in_flight(
    client: TestClient,
    auth_user_admin: User,
    db_session: Session,
    trigger_dir,
) -> None:
    _seed_backup(
        db_session,
        status="running",
        file_path="./backups/in-progress.dump",
        type="manual",
    )
    resp = client.post(
        "/api/admin/backups/trigger", json={"type": "manual"}
    )
    assert resp.status_code == 409


def test_trigger_forbidden_for_reader(
    client: TestClient, auth_user_reader: User, trigger_dir
) -> None:
    resp = client.post(
        "/api/admin/backups/trigger", json={"type": "manual"}
    )
    assert resp.status_code == 403
