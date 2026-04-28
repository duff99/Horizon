"""Endpoints /api/commitments : CRUD + match/unmatch/suggest."""
from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import (
    accessible_entity_ids_subquery,
    get_current_user,
    require_entity_access,
)
from app.models.bank_account import BankAccount
from app.models.commitment import Commitment, CommitmentDirection, CommitmentStatus
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.commitment import (
    CommitmentCreate,
    CommitmentListResponse,
    CommitmentMatchRequest,
    CommitmentRead,
    CommitmentSuggestionResponse,
    CommitmentUpdate,
    TransactionBrief,
)
from app.services.audit import record_audit, to_dict_for_audit
from app.services.commitment_matching import suggest_matches

router = APIRouter(prefix="/api/commitments", tags=["commitments"])


def _accessible_entity_ids(session: Session, user: User) -> list[int]:
    return list(
        session.scalars(accessible_entity_ids_subquery(session=session, user=user))
    )


def _get_or_404_with_access(
    session: Session, user: User, commitment_id: int,
) -> Commitment:
    c = session.get(Commitment, commitment_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Engagement introuvable")
    require_entity_access(session=session, user=user, entity_id=c.entity_id)
    return c


@router.get("", response_model=CommitmentListResponse)
def list_commitments(
    entity_id: int | None = Query(default=None),
    status_: Literal["pending", "paid", "cancelled"] | None = Query(
        default=None, alias="status"
    ),
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = Query(default=None),
    direction: Literal["in", "out"] | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=500),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> CommitmentListResponse:
    accessible = _accessible_entity_ids(session, user)
    if entity_id is not None:
        if entity_id not in accessible:
            raise HTTPException(status_code=403, detail="Entité non accessible")
        where = [Commitment.entity_id == entity_id]
    else:
        where = [Commitment.entity_id.in_(accessible)]

    if status_:
        where.append(Commitment.status == CommitmentStatus(status_))
    if from_:
        where.append(Commitment.expected_date >= from_)
    if to:
        where.append(Commitment.expected_date <= to)
    if direction:
        where.append(Commitment.direction == CommitmentDirection(direction))

    total = session.scalar(
        select(func.count(Commitment.id)).where(and_(*where))
    ) or 0

    q = (
        select(Commitment)
        .where(and_(*where))
        .order_by(Commitment.expected_date.desc())
        .limit(per_page)
        .offset((page - 1) * per_page)
    )
    rows = session.execute(q).scalars().all()
    items = [CommitmentRead.model_validate(r) for r in rows]
    return CommitmentListResponse(
        items=items, total=total, page=page, per_page=per_page,
    )


@router.post("", response_model=CommitmentRead, status_code=status.HTTP_201_CREATED)
def create_commitment(
    payload: CommitmentCreate,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> CommitmentRead:
    require_entity_access(session=session, user=user, entity_id=payload.entity_id)

    if payload.bank_account_id is not None:
        ba = session.get(BankAccount, payload.bank_account_id)
        if ba is None or ba.entity_id != payload.entity_id:
            raise HTTPException(
                status_code=400,
                detail="Le compte bancaire ne correspond pas à l'entité",
            )

    c = Commitment(
        entity_id=payload.entity_id,
        counterparty_id=payload.counterparty_id,
        category_id=payload.category_id,
        bank_account_id=payload.bank_account_id,
        direction=CommitmentDirection(payload.direction),
        amount_cents=payload.amount_cents,
        issue_date=payload.issue_date,
        expected_date=payload.expected_date,
        reference=payload.reference,
        description=payload.description,
        pdf_attachment_id=payload.pdf_attachment_id,
        created_by_id=user.id,
    )
    session.add(c)
    session.flush()
    record_audit(
        session, user=user, action="create", entity=c,
        before=None, after=to_dict_for_audit(c), request=request,
    )
    session.commit()
    session.refresh(c)
    return CommitmentRead.model_validate(c)


@router.get("/{commitment_id}", response_model=CommitmentRead)
def get_commitment(
    commitment_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> CommitmentRead:
    c = _get_or_404_with_access(session, user, commitment_id)
    return CommitmentRead.model_validate(c)


@router.patch("/{commitment_id}", response_model=CommitmentRead)
def update_commitment(
    commitment_id: int,
    payload: CommitmentUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> CommitmentRead:
    c = _get_or_404_with_access(session, user, commitment_id)
    before_snapshot = to_dict_for_audit(c)
    updates = payload.model_dump(exclude_unset=True)
    # Validation dates si elles changent
    issue = updates.get("issue_date", c.issue_date)
    expected = updates.get("expected_date", c.expected_date)
    if issue > expected:
        raise HTTPException(
            status_code=422, detail="issue_date doit être <= expected_date",
        )
    if (expected - issue).days > 365:
        raise HTTPException(
            status_code=422,
            detail="L'écart entre issue_date et expected_date ne doit pas dépasser 365 jours",
        )
    for field, value in updates.items():
        if field == "direction" and value is not None:
            setattr(c, field, CommitmentDirection(value))
        elif field == "status" and value is not None:
            setattr(c, field, CommitmentStatus(value))
        else:
            setattr(c, field, value)
    session.flush()
    record_audit(
        session, user=user, action="update", entity=c,
        before=before_snapshot, after=to_dict_for_audit(c), request=request,
    )
    session.commit()
    session.refresh(c)
    return CommitmentRead.model_validate(c)


@router.delete("/{commitment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_commitment(
    commitment_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> None:
    """Soft-delete : passe le statut à `cancelled`."""
    c = _get_or_404_with_access(session, user, commitment_id)
    before_snapshot = to_dict_for_audit(c)
    c.status = CommitmentStatus.CANCELLED
    session.flush()
    # Soft-delete = update (status -> cancelled) ; l'entité existe toujours.
    record_audit(
        session, user=user, action="update", entity=c,
        before=before_snapshot, after=to_dict_for_audit(c), request=request,
    )
    session.commit()


@router.post("/{commitment_id}/match", response_model=CommitmentRead)
def match_commitment(
    commitment_id: int,
    payload: CommitmentMatchRequest,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> CommitmentRead:
    c = _get_or_404_with_access(session, user, commitment_id)
    before_snapshot = to_dict_for_audit(c)
    tx = session.get(Transaction, payload.transaction_id)
    if tx is None:
        raise HTTPException(status_code=404, detail="Transaction introuvable")
    # Vérifier accès à l'entité de la transaction
    ba = session.get(BankAccount, tx.bank_account_id)
    if ba is None:
        raise HTTPException(status_code=404, detail="Compte bancaire introuvable")
    require_entity_access(session=session, user=user, entity_id=ba.entity_id)

    # Conflict si transaction déjà liée à un *autre* commitment
    existing = session.scalar(
        select(Commitment.id).where(
            and_(
                Commitment.matched_transaction_id == tx.id,
                Commitment.id != c.id,
            )
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="Cette transaction est déjà liée à un autre engagement",
        )

    c.matched_transaction_id = tx.id
    c.status = CommitmentStatus.PAID
    session.flush()
    record_audit(
        session, user=user, action="update", entity=c,
        before=before_snapshot, after=to_dict_for_audit(c), request=request,
    )
    session.commit()
    session.refresh(c)
    return CommitmentRead.model_validate(c)


@router.post("/{commitment_id}/unmatch", response_model=CommitmentRead)
def unmatch_commitment(
    commitment_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> CommitmentRead:
    c = _get_or_404_with_access(session, user, commitment_id)
    before_snapshot = to_dict_for_audit(c)
    c.matched_transaction_id = None
    c.status = CommitmentStatus.PENDING
    session.flush()
    record_audit(
        session, user=user, action="update", entity=c,
        before=before_snapshot, after=to_dict_for_audit(c), request=request,
    )
    session.commit()
    session.refresh(c)
    return CommitmentRead.model_validate(c)


@router.get(
    "/{commitment_id}/suggest-matches",
    response_model=CommitmentSuggestionResponse,
)
def suggest_matches_endpoint(
    commitment_id: int,
    limit: int = Query(default=10, ge=1, le=50),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> CommitmentSuggestionResponse:
    c = _get_or_404_with_access(session, user, commitment_id)
    candidates = suggest_matches(session, c, limit=limit)
    # Enrichir le label du compte bancaire
    ba_ids = {tx.bank_account_id for tx, _ in candidates}
    ba_map: dict[int, str] = {}
    if ba_ids:
        for row in session.execute(
            select(BankAccount.id, BankAccount.name).where(
                BankAccount.id.in_(ba_ids)
            )
        ):
            ba_map[row[0]] = row[1]
    items = [
        TransactionBrief(
            id=tx.id,
            operation_date=tx.operation_date,
            label=tx.label,
            amount=tx.amount,
            bank_account_label=ba_map.get(tx.bank_account_id),
        )
        for tx, _score in candidates
    ]
    return CommitmentSuggestionResponse(candidates=items)
