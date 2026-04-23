"""Endpoint admin : consultation du journal d'audit.

GET /api/admin/audit-log — liste paginée, filtrable, admin only.
POST /api/admin/audit-log/prune — supprime les lignes > N jours (manuel).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, delete, func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_admin
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit_log import AuditLogListResponse, AuditLogRead

router = APIRouter(
    prefix="/api/admin/audit-log",
    tags=["admin-audit"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=AuditLogListResponse)
def list_audit_log(
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    user_id: int | None = Query(default=None),
    action: str | None = Query(default=None, pattern="^(create|update|delete)$"),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> AuditLogListResponse:
    conditions = []
    if entity_type:
        conditions.append(AuditLog.entity_type == entity_type)
    if entity_id:
        conditions.append(AuditLog.entity_id == entity_id)
    if user_id is not None:
        conditions.append(AuditLog.user_id == user_id)
    if action:
        conditions.append(AuditLog.action == action)
    if from_ is not None:
        conditions.append(AuditLog.occurred_at >= from_)
    if to is not None:
        conditions.append(AuditLog.occurred_at <= to)

    where = and_(*conditions) if conditions else None

    count_q = select(func.count(AuditLog.id))
    if where is not None:
        count_q = count_q.where(where)
    total = db.scalar(count_q) or 0

    q = select(AuditLog).order_by(AuditLog.occurred_at.desc(), AuditLog.id.desc())
    if where is not None:
        q = q.where(where)
    q = q.offset(offset).limit(limit)
    rows = list(db.scalars(q))

    return AuditLogListResponse(
        items=[AuditLogRead.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/prune")
def prune_audit_log(
    days: int = Query(default=365, ge=30, le=3650),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    """Supprime les lignes audit_log plus anciennes que `days` jours.

    Rétention cible : 365 jours. Minimum autorisé : 30 jours (garde-fou).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = db.execute(delete(AuditLog).where(AuditLog.occurred_at < cutoff))
    deleted = result.rowcount or 0
    db.commit()
    return {"deleted_count": deleted, "cutoff_days": days}
