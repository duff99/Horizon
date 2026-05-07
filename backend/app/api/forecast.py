"""API prévisionnel : projection de trésorerie + suggestions de récurrences."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import (
    accessible_entity_ids_subquery,
    get_current_user,
    require_entity_access,
)
from app.models.bank_account import BankAccount
from app.models.import_record import ImportRecord, ImportStatus
from app.models.user import User
from app.schemas.forecast import (
    DetectedRecurrenceSuggestion,
    ForecastProjection,
)
from app.services.forecast import compute_projection, detect_recurring

router = APIRouter(prefix="/api/forecast", tags=["forecast"])


def _accessible_entities(db: Session, user: User) -> list[int]:
    return list(
        db.scalars(accessible_entity_ids_subquery(session=db, user=user))
    )


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
