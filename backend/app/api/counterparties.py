"""Endpoints /api/counterparties."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_entity_access
from app.models.counterparty import Counterparty, CounterpartyStatus
from app.models.user import User
from app.models.user_entity_access import UserEntityAccess
from app.schemas.counterparty import CounterpartyRead, CounterpartyUpdate
from app.services.audit import record_audit, to_dict_for_audit

router = APIRouter(prefix="/api/counterparties", tags=["counterparties"])


@router.get("", response_model=list[CounterpartyRead])
def list_counterparties(
    status: Literal["pending", "active", "ignored"] | None = Query(default=None),
    entity_id: int | None = Query(default=None),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[CounterpartyRead]:
    accessible = select(UserEntityAccess.entity_id).where(
        UserEntityAccess.user_id == user.id
    )
    q = select(Counterparty).where(Counterparty.entity_id.in_(accessible))
    if entity_id is not None:
        require_entity_access(session=session, user=user, entity_id=entity_id)
        q = q.where(Counterparty.entity_id == entity_id)
    if status:
        q = q.where(Counterparty.status == CounterpartyStatus(status))
    q = q.order_by(Counterparty.name.asc())
    rows = session.execute(q).scalars().all()
    return [CounterpartyRead.model_validate(r) for r in rows]


@router.patch("/{counterparty_id}", response_model=CounterpartyRead)
def update_counterparty(
    counterparty_id: int,
    payload: CounterpartyUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> CounterpartyRead:
    cp = session.get(Counterparty, counterparty_id)
    if cp is None:
        raise HTTPException(status_code=404, detail="Contrepartie introuvable")
    require_entity_access(session=session, user=user, entity_id=cp.entity_id)

    before_snapshot = to_dict_for_audit(cp)
    if payload.status is not None:
        cp.status = CounterpartyStatus(payload.status)
    if payload.name is not None:
        cp.name = payload.name.strip()
        # normalized_name doit rester cohérent
        from app.services.imports import _normalize_counterparty_name
        cp.normalized_name = _normalize_counterparty_name(cp.name)
    session.flush()
    record_audit(
        session, user=user, action="update", entity=cp,
        before=before_snapshot, after=to_dict_for_audit(cp), request=request,
    )
    session.commit()
    session.refresh(cp)
    return CounterpartyRead.model_validate(cp)
