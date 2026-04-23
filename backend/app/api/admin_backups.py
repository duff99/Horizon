"""Endpoint admin : lecture des 50 derniers backups (table `backup_history`).

Utilisé par l'admin pour monitorer que les backups tournent bien en production.
Read-only, aucune mutation depuis l'API (les mutations viennent du script shell).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_admin
from app.models.backup_history import BackupHistory
from app.schemas.backup_history import BackupHistoryRead

router = APIRouter(
    prefix="/api/admin/backups",
    tags=["admin-backups"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=list[BackupHistoryRead])
def list_backups(db: Session = Depends(get_db)) -> list[BackupHistory]:
    """Retourne les 50 derniers backups, du plus récent au plus ancien."""
    return list(
        db.scalars(
            select(BackupHistory)
            .order_by(BackupHistory.started_at.desc())
            .limit(50)
        )
    )
