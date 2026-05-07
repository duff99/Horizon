"""Endpoint admin : consultation du journal d'audit.

GET /api/admin/audit-log — liste paginée, filtrable, admin only.
GET /api/admin/audit-log/export — export CSV (admin only).

La purge des lignes anciennes se fait via SQL direct (intervention technique) :
  DELETE FROM audit_log WHERE occurred_at < NOW() - INTERVAL '365 days';
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.api._export_helpers import XLSX_AVAILABLE, export_response
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
    action: str | None = Query(
        default=None,
        pattern="^(create|update|delete|merge|login|login_failed|logout)$",
    ),
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


@router.get("/export")
def export_audit_log(
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    user_id: int | None = Query(default=None),
    action: str | None = Query(
        default=None,
        pattern="^(create|update|delete|merge|login|login_failed|logout)$",
    ),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    format: Literal["csv", "xlsx"] = Query(default="csv"),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Export CSV (ou XLSX si disponible) du journal d'audit — admin only.

    Réutilise les mêmes filtres que GET /api/admin/audit-log.
    Pas de pagination : toutes les lignes filtrées sont exportées.
    """
    if format == "xlsx" and not XLSX_AVAILABLE:
        raise HTTPException(status_code=400, detail="Format XLSX non disponible sur ce serveur.")

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
    q = select(AuditLog).order_by(AuditLog.occurred_at.desc(), AuditLog.id.desc())
    if where is not None:
        q = q.where(where)
    entries = list(db.scalars(q))

    headers = ["Date/heure", "Utilisateur", "Action", "Type entite", "ID entite", "Adresse IP"]
    rows = [
        [
            e.occurred_at.strftime("%Y-%m-%d %H:%M:%S") if e.occurred_at else "",
            e.user_email or "",
            e.action,
            e.entity_type,
            e.entity_id,
            e.ip_address or "",
        ]
        for e in entries
    ]

    today = date.today().isoformat()
    filename_base = f"audit-log_{today}"
    try:
        return export_response(headers, rows, filename_base, format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
