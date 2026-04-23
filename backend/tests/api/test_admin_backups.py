"""Tests pour GET /api/admin/backups (lecture des entrées backup_history)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

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
) -> BackupHistory:
    row = BackupHistory(
        status=status,
        file_path=file_path,
        started_at=datetime.now(UTC) - timedelta(minutes=offset_min),
        size_bytes=1234,
        sha256="a" * 64,
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
    assert first["size_bytes"] == 1234
    assert first["row_counts_json"] == {"users": 1, "transactions": 42}
