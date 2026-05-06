"""Endpoints /api/counterparties."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi import status as http_status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import (
    accessible_entity_ids_subquery,
    get_current_user,
    require_entity_access,
)
from app.models.commitment import Commitment, CommitmentStatus
from app.models.counterparty import Counterparty, CounterpartyStatus
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.counterparty import (
    CounterpartyCreate,
    CounterpartyRead,
    CounterpartyUpdate,
    CounterpartyWithAggregates,
)
from app.services.audit import record_audit, to_dict_for_audit

router = APIRouter(prefix="/api/counterparties", tags=["counterparties"])


@router.get("", response_model=list[CounterpartyWithAggregates])
def list_counterparties(
    entity_id: int | None = Query(default=None),
    include_ignored: bool = Query(default=False),
    search: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[CounterpartyWithAggregates]:
    accessible = accessible_entity_ids_subquery(session=session, user=user)

    # Subqueries scalaires corrélées : on évite le produit cartésien LEFT
    # JOIN Transaction × Commitment qui dupliquerait les compteurs
    # (1 tiers avec 2 tx + 1 engagement → 2 lignes jointes → engagement
    # compté 2 fois si on agrégeait sur la jointure).
    tx_count_sq = (
        select(func.count(Transaction.id))
        .where(Transaction.counterparty_id == Counterparty.id)
        .correlate(Counterparty)
        .scalar_subquery()
    )
    tx_volume_sq = (
        select(func.coalesce(func.sum(func.abs(Transaction.amount)), 0))
        .where(Transaction.counterparty_id == Counterparty.id)
        .correlate(Counterparty)
        .scalar_subquery()
    )
    tx_last_sq = (
        select(func.max(Transaction.operation_date))
        .where(Transaction.counterparty_id == Counterparty.id)
        .correlate(Counterparty)
        .scalar_subquery()
    )
    pending_commit_sq = (
        select(func.count(Commitment.id))
        .where(
            Commitment.counterparty_id == Counterparty.id,
            Commitment.status == CommitmentStatus.PENDING,
        )
        .correlate(Counterparty)
        .scalar_subquery()
    )

    q = (
        select(
            Counterparty.id,
            Counterparty.entity_id,
            Counterparty.name,
            Counterparty.status,
            tx_count_sq.label("transaction_count"),
            tx_volume_sq.label("volume_cumulated"),
            tx_last_sq.label("last_operation_date"),
            pending_commit_sq.label("pending_commitment_count"),
        )
        .where(Counterparty.entity_id.in_(accessible))
    )

    if entity_id is not None:
        require_entity_access(session=session, user=user, entity_id=entity_id)
        q = q.where(Counterparty.entity_id == entity_id)
    if not include_ignored:
        q = q.where(Counterparty.status != CounterpartyStatus.IGNORED)
    if search:
        q = q.where(Counterparty.name.ilike(f"%{search}%"))

    q = q.order_by(tx_volume_sq.desc(), Counterparty.name.asc())

    rows = session.execute(q).all()
    return [
        CounterpartyWithAggregates(
            id=r.id,
            entity_id=r.entity_id,
            name=r.name,
            status=r.status.value,
            transaction_count=r.transaction_count,
            volume_cumulated=float(r.volume_cumulated),
            last_operation_date=r.last_operation_date,
            pending_commitment_count=r.pending_commitment_count,
        )
        for r in rows
    ]


@router.post(
    "",
    response_model=CounterpartyRead,
    status_code=http_status.HTTP_201_CREATED,
)
def create_counterparty(
    payload: CounterpartyCreate,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> CounterpartyRead:
    require_entity_access(session=session, user=user, entity_id=payload.entity_id)
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nom requis")
    from app.services.imports import _normalize_counterparty_name
    cp = Counterparty(
        entity_id=payload.entity_id,
        name=name,
        normalized_name=_normalize_counterparty_name(name),
        status=CounterpartyStatus.ACTIVE,
    )
    session.add(cp)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409, detail="Un tiers avec ce nom existe déjà"
        )
    record_audit(
        session, user=user, action="create", entity=cp,
        before=None, after=to_dict_for_audit(cp), request=request,
    )
    session.commit()
    session.refresh(cp)
    return CounterpartyRead.model_validate(cp)


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
