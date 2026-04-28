"""Endpoint GET /api/admin/client-errors — listing pour admin.

Lecture seule. Filtre optionnel par severity, source, user_id, période.
Pagination simple (limit/offset).
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_admin
from app.models.client_error import ClientError
from app.models.user import User
from app.schemas.client_error import (
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
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
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
            )
        )

    return ClientErrorListResponse(
        items=items, total=total, limit=limit, offset=offset
    )
