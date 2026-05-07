"""Endpoint GET /api/admin/client-errors — listing pour admin.

Lecture seule. Filtre optionnel par severity, source, user_id, période, acknowledged.
Pagination simple (limit/offset).
Acquittement via PATCH /{id}/acknowledge.
"""
from __future__ import annotations

from datetime import datetime as dt_datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_admin
from app.models.client_error import ClientError
from app.models.user import User
from app.schemas.client_error import (
    ClientErrorAcknowledgeResponse,
    ClientErrorListResponse,
    ClientErrorRead,
)

router = APIRouter(
    prefix="/api/admin/client-errors",
    tags=["admin-client-errors"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=ClientErrorListResponse)
def list_client_errors(
    severity: Literal["debug", "info", "warning", "error", "fatal"] | None = Query(
        default=None
    ),
    source: str | None = Query(default=None),
    user_id: int | None = Query(default=None),
    since: dt_datetime | None = Query(default=None),
    until: dt_datetime | None = Query(default=None),
    acknowledged: bool | None = Query(default=None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> ClientErrorListResponse:
    base = select(ClientError, User.email).outerjoin(
        User, User.id == ClientError.user_id
    )
    count_base = select(func.count()).select_from(ClientError)

    if severity is not None:
        base = base.where(ClientError.severity == severity)
        count_base = count_base.where(ClientError.severity == severity)
    if source is not None:
        base = base.where(ClientError.source == source)
        count_base = count_base.where(ClientError.source == source)
    if user_id is not None:
        base = base.where(ClientError.user_id == user_id)
        count_base = count_base.where(ClientError.user_id == user_id)
    if since is not None:
        base = base.where(ClientError.occurred_at >= since)
        count_base = count_base.where(ClientError.occurred_at >= since)
    if until is not None:
        base = base.where(ClientError.occurred_at <= until)
        count_base = count_base.where(ClientError.occurred_at <= until)
    if acknowledged is True:
        base = base.where(ClientError.acknowledged_at.isnot(None))
        count_base = count_base.where(ClientError.acknowledged_at.isnot(None))
    elif acknowledged is False:
        base = base.where(ClientError.acknowledged_at.is_(None))
        count_base = count_base.where(ClientError.acknowledged_at.is_(None))

    total = db.scalar(count_base) or 0

    rows = db.execute(
        base.order_by(ClientError.occurred_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    items: list[ClientErrorRead] = []
    for ce, email in rows:
        items.append(
            ClientErrorRead(
                id=ce.id,
                occurred_at=ce.occurred_at,
                user_id=ce.user_id,
                user_email=email,
                severity=ce.severity,
                source=ce.source,
                message=ce.message,
                stack=ce.stack,
                url=ce.url,
                user_agent=ce.user_agent,
                request_id=ce.request_id,
                context_json=ce.context_json,
                acknowledged_at=ce.acknowledged_at,
            )
        )

    return ClientErrorListResponse(
        items=items, total=total, limit=limit, offset=offset
    )


@router.patch("/{error_id}/acknowledge", response_model=ClientErrorAcknowledgeResponse)
def acknowledge_client_error(
    error_id: int,
    db: Session = Depends(get_db),
) -> ClientErrorAcknowledgeResponse:
    """Marque une erreur client comme acquittée (examinée et traitée)."""
    ce = db.get(ClientError, error_id)
    if ce is None:
        raise HTTPException(status_code=404, detail="Erreur introuvable")
    ce.acknowledged_at = dt_datetime.utcnow()
    db.commit()
    db.refresh(ce)
    return ClientErrorAcknowledgeResponse(id=ce.id, acknowledged_at=ce.acknowledged_at)
