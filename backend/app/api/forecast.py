"""API CRUD pour les entrées prévisionnelles + projection de trésorerie."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_entity_access
from app.models.bank_account import BankAccount
from app.models.forecast_entry import ForecastEntry
from app.models.import_record import ImportRecord, ImportStatus
from app.models.user import User
from app.models.user_entity_access import UserEntityAccess
from app.schemas.forecast import (
    DetectedRecurrenceSuggestion,
    ForecastEntryCreate,
    ForecastEntryRead,
    ForecastEntryUpdate,
    ForecastProjection,
)
from app.services.forecast import compute_projection, detect_recurring

router = APIRouter(prefix="/api/forecast", tags=["forecast"])


def _accessible_entities(db: Session, user: User) -> list[int]:
    return list(
        db.scalars(
            select(UserEntityAccess.entity_id).where(
                UserEntityAccess.user_id == user.id
            )
        )
    )


@router.get("/entries", response_model=list[ForecastEntryRead])
def list_entries(
    entity_id: int | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ForecastEntryRead]:
    accessible = _accessible_entities(db, user)
    if entity_id is not None:
        if entity_id not in accessible:
            raise HTTPException(status_code=403, detail="Entité non accessible")
        where = [ForecastEntry.entity_id == entity_id]
    else:
        where = [ForecastEntry.entity_id.in_(accessible)]

    rows = db.execute(
        select(ForecastEntry).where(and_(*where)).order_by(ForecastEntry.due_date)
    ).scalars().all()
    return [ForecastEntryRead.model_validate(r) for r in rows]


@router.post(
    "/entries", response_model=ForecastEntryRead, status_code=status.HTTP_201_CREATED,
)
def create_entry(
    payload: ForecastEntryCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ForecastEntryRead:
    require_entity_access(session=db, user=user, entity_id=payload.entity_id)
    if payload.bank_account_id is not None:
        ba = db.get(BankAccount, payload.bank_account_id)
        if ba is None or ba.entity_id != payload.entity_id:
            raise HTTPException(
                status_code=400,
                detail="Le compte bancaire ne correspond pas à l'entité",
            )

    entry = ForecastEntry(
        entity_id=payload.entity_id,
        bank_account_id=payload.bank_account_id,
        label=payload.label,
        amount=payload.amount,
        due_date=payload.due_date,
        category_id=payload.category_id,
        counterparty_id=payload.counterparty_id,
        recurrence=payload.recurrence,
        recurrence_until=payload.recurrence_until,
        notes=payload.notes,
        created_by_id=user.id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return ForecastEntryRead.model_validate(entry)


@router.patch("/entries/{entry_id}", response_model=ForecastEntryRead)
def update_entry(
    entry_id: int,
    payload: ForecastEntryUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ForecastEntryRead:
    entry = db.get(ForecastEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entrée introuvable")
    require_entity_access(session=db, user=user, entity_id=entry.entity_id)

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(entry, field, value)
    db.commit()
    db.refresh(entry)
    return ForecastEntryRead.model_validate(entry)


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(
    entry_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    entry = db.get(ForecastEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entrée introuvable")
    require_entity_access(session=db, user=user, entity_id=entry.entity_id)
    db.delete(entry)
    db.commit()


@router.get("/projection", response_model=ForecastProjection)
def get_projection(
    horizon_days: int = Query(90, ge=7, le=365),
    entity_id: int | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ForecastProjection:
    accessible = _accessible_entities(db, user)
    if entity_id is not None and entity_id not in accessible:
        raise HTTPException(status_code=403, detail="Entité non accessible")

    entity_filter = (
        [BankAccount.entity_id == entity_id]
        if entity_id is not None
        else [BankAccount.entity_id.in_(accessible)]
    )
    bank_account_ids = list(
        db.scalars(select(BankAccount.id).where(and_(*entity_filter)))
    )

    # Solde actuel = somme des derniers closing_balance (même logique que dashboard)
    starting_balance = Decimal("0")
    starting_date = date.today()
    if bank_account_ids:
        latest_per_account = (
            select(
                ImportRecord.bank_account_id,
                func.max(ImportRecord.period_end).label("last_end"),
            )
            .where(
                and_(
                    ImportRecord.bank_account_id.in_(bank_account_ids),
                    ImportRecord.status == ImportStatus.COMPLETED,
                    ImportRecord.closing_balance.is_not(None),
                    ImportRecord.period_end.is_not(None),
                )
            )
            .group_by(ImportRecord.bank_account_id)
            .subquery()
        )
        rows = db.execute(
            select(
                ImportRecord.closing_balance, ImportRecord.period_end,
            ).join(
                latest_per_account,
                and_(
                    ImportRecord.bank_account_id == latest_per_account.c.bank_account_id,
                    ImportRecord.period_end == latest_per_account.c.last_end,
                ),
            )
        ).all()
        starting_balance = sum(
            (Decimal(r.closing_balance) for r in rows), Decimal("0")
        )
        starting_date = max(
            (r.period_end for r in rows if r.period_end), default=date.today()
        )

    return compute_projection(
        db,
        bank_account_ids=bank_account_ids,
        accessible_entity_ids=accessible,
        entity_id=entity_id,
        starting_balance=starting_balance,
        starting_date=starting_date,
        horizon_days=horizon_days,
    )


@router.get("/recurring-suggestions", response_model=list[DetectedRecurrenceSuggestion])
def get_recurring_suggestions(
    entity_id: int = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DetectedRecurrenceSuggestion]:
    require_entity_access(session=db, user=user, entity_id=entity_id)
    bank_account_ids = list(
        db.scalars(
            select(BankAccount.id).where(BankAccount.entity_id == entity_id)
        )
    )
    if not bank_account_ids:
        return []
    return detect_recurring(
        db, entity_id=entity_id, bank_account_ids=bank_account_ids,
    )
