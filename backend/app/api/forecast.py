"""API prévisionnel : projection de trésorerie + suggestions de récurrences."""
from __future__ import annotations

from datetime import date, timedelta
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
from app.models.forecast_line import ForecastLine
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.forecast import (
    DetectedRecurrenceSuggestion,
    ForecastProjection,
)
from app.schemas.treasury import Rolling13WPoint, Rolling13WResponse
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


@router.get("/rolling-13w", response_model=Rolling13WResponse)
def get_rolling_13w(
    entity_id: int = Query(...),
    scenario_id: int | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Rolling13WResponse:
    """Vue hebdomadaire court terme : W-1 à W+11 (13 semaines glissantes).

    Chaque point contient :
    - realized_cents : Σ transactions réelles de la semaine (débit net)
    - forecast_cents : Σ forecast_lines du scénario dont l'expected_date tombe dans la semaine
    - is_past : True si la semaine est déjà passée
    """
    require_entity_access(session=db, user=user, entity_id=entity_id)

    bank_account_ids = list(
        db.scalars(select(BankAccount.id).where(BankAccount.entity_id == entity_id))
    )

    today = date.today()
    # Lundi de la semaine courante
    monday_this_week = today - timedelta(days=today.weekday())
    # W-1 = semaine précédente
    window_start = monday_this_week - timedelta(weeks=1)

    points: list[Rolling13WPoint] = []
    for i in range(13):
        week_start = window_start + timedelta(weeks=i)
        week_end = week_start + timedelta(days=6)

        # ISO week label
        iso = week_start.isocalendar()
        week_label = f"{iso.year}-W{iso.week:02d}"

        # Transactions réalisées
        realized_cents = 0
        if bank_account_ids:
            row = db.execute(
                select(func.sum(Transaction.amount)).where(
                    and_(
                        Transaction.bank_account_id.in_(bank_account_ids),
                        Transaction.operation_date >= week_start,
                        Transaction.operation_date <= week_end,
                        Transaction.is_aggregation_parent.is_(False),
                    )
                )
            ).scalar()
            if row is not None:
                realized_cents = int(Decimal(str(row)) * 100)

        # Forecast lines : agrégation par expected_date dans la semaine
        forecast_cents = 0
        if scenario_id is not None:
            # ForecastLine.amount_cents est en centimes, méthode SINGLE_MONTH_FIXED.
            # Pour les autres méthodes on utilise amount_cents directement s'il est défini.
            # expected_date n'existe pas sur ForecastLine → on utilise start_month si disponible.
            # Les lignes sans date → on les ignore pour la vue hebdomadaire.
            frows = db.execute(
                select(func.sum(ForecastLine.amount_cents)).where(
                    and_(
                        ForecastLine.scenario_id == scenario_id,
                        ForecastLine.entity_id == entity_id,
                        ForecastLine.start_month >= week_start,
                        ForecastLine.start_month <= week_end,
                        ForecastLine.amount_cents.is_not(None),
                    )
                )
            ).scalar()
            if frows is not None:
                forecast_cents = int(frows)

        points.append(
            Rolling13WPoint(
                week_label=week_label,
                week_start=week_start,
                realized_cents=realized_cents,
                forecast_cents=forecast_cents,
                is_past=week_start < monday_this_week,
            )
        )

    return Rolling13WResponse(
        entity_id=entity_id,
        scenario_id=scenario_id,
        points=points,
    )
