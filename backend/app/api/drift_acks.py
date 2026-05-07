"""Endpoints snooze/acquittement de dérive — G12."""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_entity_access
from app.models.drift_ack import DriftAck
from app.models.user import User
from app.schemas.drift_ack import DriftAckRead, DriftSnoozeRequest

router = APIRouter(prefix="/api/analysis/drift-acks", tags=["analysis"])


@router.post("/", response_model=DriftAckRead, status_code=201)
def snooze_drift(
    body: DriftSnoozeRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> DriftAckRead:
    """Créer un acquittement snooze pour une catégorie × entité donnée."""
    require_entity_access(session=session, user=user, entity_id=body.entity_id)
    ack = DriftAck(
        entity_id=body.entity_id,
        category_id=body.category_id,
        snoozed_until=date.today() + timedelta(days=body.snooze_days),
        acknowledged_by_id=user.id,
        note=body.note,
    )
    session.add(ack)
    session.commit()
    session.refresh(ack)
    return DriftAckRead.model_validate(ack)


@router.delete("/{ack_id}", status_code=204)
def delete_drift_ack(
    ack_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> None:
    """Annuler un acquittement snooze (suppression réelle de l'enregistrement)."""
    ack = session.get(DriftAck, ack_id)
    if ack is None:
        raise HTTPException(status_code=404, detail="Acquittement introuvable")
    require_entity_access(session=session, user=user, entity_id=ack.entity_id)
    session.delete(ack)
    session.commit()


@router.get("/", response_model=list[DriftAckRead])
def list_drift_acks(
    entity_id: int = Query(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[DriftAckRead]:
    """Lister les acquittements actifs (snoozed_until >= aujourd'hui) pour une entité."""
    require_entity_access(session=session, user=user, entity_id=entity_id)
    today = date.today()
    acks = session.scalars(
        select(DriftAck)
        .where(
            DriftAck.entity_id == entity_id,
            DriftAck.snoozed_until >= today,
        )
        .order_by(DriftAck.acknowledged_at.desc())
    ).all()
    return [DriftAckRead.model_validate(a) for a in acks]
