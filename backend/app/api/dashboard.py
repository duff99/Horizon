"""Endpoint agrégat pour le tableau de bord."""
from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models.bank_account import BankAccount
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction, TransactionCategorizationSource
from app.models.user import User
from app.models.user_entity_access import UserEntityAccess
from app.schemas.dashboard import (
    DailyBalance,
    DailyCashflow,
    DashboardPeriod,
    DashboardSummary,
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

_FR_MONTHS = (
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
)


def _resolve_period(period: DashboardPeriod, today: date) -> tuple[date, date, str]:
    if period == DashboardPeriod.CURRENT_MONTH:
        start = today.replace(day=1)
        end = today
        label = f"{_FR_MONTHS[today.month - 1]} {today.year}"
    elif period == DashboardPeriod.PREVIOUS_MONTH:
        first_of_current = today.replace(day=1)
        end = first_of_current - timedelta(days=1)
        start = end.replace(day=1)
        label = f"{_FR_MONTHS[end.month - 1]} {end.year}"
    elif period == DashboardPeriod.LAST_30D:
        start = today - timedelta(days=29)
        end = today
        label = "30 derniers jours"
    elif period == DashboardPeriod.LAST_90D:
        start = today - timedelta(days=89)
        end = today
        label = "90 derniers jours"
    else:  # pragma: no cover — enum exhaustivement couvert
        raise ValueError(f"Période inconnue : {period!r}")
    return start, end, label


@router.get("/summary", response_model=DashboardSummary)
def get_summary(
    period: DashboardPeriod = Query(DashboardPeriod.CURRENT_MONTH),
    entity_id: int | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardSummary:
    today = date.today()
    period_start, period_end, period_label = _resolve_period(period, today)

    accessible_entity_ids = list(
        db.scalars(
            select(UserEntityAccess.entity_id).where(
                UserEntityAccess.user_id == user.id
            )
        )
    )

    if entity_id is not None and entity_id not in accessible_entity_ids:
        raise HTTPException(status_code=403, detail="Entité non accessible")

    entity_filter = (
        [BankAccount.entity_id == entity_id]
        if entity_id is not None
        else [BankAccount.entity_id.in_(accessible_entity_ids)]
    )

    bank_account_ids = list(
        db.scalars(select(BankAccount.id).where(and_(*entity_filter)))
    )

    prev_start, prev_end = _previous_period(period_start, period_end)

    if not bank_account_ids:
        return DashboardSummary(
            period=period,
            period_label=period_label,
            period_start=period_start,
            period_end=period_end,
            total_balance=Decimal("0"),
            total_balance_asof=None,
            inflows=Decimal("0"),
            outflows=Decimal("0"),
            uncategorized_count=0,
            prev_period_start=prev_start,
            prev_period_end=prev_end,
            prev_inflows=Decimal("0"),
            prev_outflows=Decimal("0"),
            daily=[],
            balance_trend=[],
        )

    total_balance, asof = _compute_total_balance(db, bank_account_ids)

    base_where = and_(
        Transaction.bank_account_id.in_(bank_account_ids),
        Transaction.operation_date >= period_start,
        Transaction.operation_date <= period_end,
        Transaction.is_aggregation_parent.is_(False),
    )

    totals_row = db.execute(
        select(
            func.coalesce(
                func.sum(
                    case((Transaction.amount > 0, Transaction.amount), else_=0)
                ),
                0,
            ).label("inflows"),
            func.coalesce(
                func.sum(
                    case((Transaction.amount < 0, Transaction.amount), else_=0)
                ),
                0,
            ).label("outflows"),
        ).where(base_where)
    ).one()

    uncategorized_count = db.execute(
        select(func.count())
        .select_from(Transaction)
        .where(
            and_(
                base_where,
                Transaction.categorized_by == TransactionCategorizationSource.NONE,
            )
        )
    ).scalar_one()

    daily_rows = db.execute(
        select(
            Transaction.operation_date.label("d"),
            func.coalesce(
                func.sum(
                    case((Transaction.amount > 0, Transaction.amount), else_=0)
                ),
                0,
            ).label("inflows"),
            func.coalesce(
                func.sum(
                    case((Transaction.amount < 0, Transaction.amount), else_=0)
                ),
                0,
            ).label("outflows"),
        )
        .where(base_where)
        .group_by(Transaction.operation_date)
        .order_by(Transaction.operation_date)
    ).all()

    daily = [
        DailyCashflow(
            date=r.d, inflows=Decimal(r.inflows), outflows=Decimal(r.outflows)
        )
        for r in daily_rows
    ]

    prev_totals_row = db.execute(
        select(
            func.coalesce(
                func.sum(
                    case((Transaction.amount > 0, Transaction.amount), else_=0)
                ),
                0,
            ).label("inflows"),
            func.coalesce(
                func.sum(
                    case((Transaction.amount < 0, Transaction.amount), else_=0)
                ),
                0,
            ).label("outflows"),
        ).where(
            and_(
                Transaction.bank_account_id.in_(bank_account_ids),
                Transaction.operation_date >= prev_start,
                Transaction.operation_date <= prev_end,
                Transaction.is_aggregation_parent.is_(False),
            )
        )
    ).one()

    balance_trend = _compute_balance_trend(
        db,
        bank_account_ids=bank_account_ids,
        total_balance=total_balance,
        end_date=period_end,
        days=90,
    )

    return DashboardSummary(
        period=period,
        period_label=period_label,
        period_start=period_start,
        period_end=period_end,
        total_balance=total_balance,
        total_balance_asof=asof,
        inflows=Decimal(totals_row.inflows),
        outflows=Decimal(totals_row.outflows),
        uncategorized_count=uncategorized_count,
        prev_period_start=prev_start,
        prev_period_end=prev_end,
        prev_inflows=Decimal(prev_totals_row.inflows),
        prev_outflows=Decimal(prev_totals_row.outflows),
        daily=daily,
        balance_trend=balance_trend,
    )


def _previous_period(start: date, end: date) -> tuple[date, date]:
    """Période précédente de même durée, se terminant la veille de `start`."""
    length_days = (end - start).days
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=length_days)
    return prev_start, prev_end


def _compute_balance_trend(
    db: Session,
    *,
    bank_account_ids: list[int],
    total_balance: Decimal,
    end_date: date,
    days: int,
) -> list[DailyBalance]:
    """Reconstruit le solde estimé jour par jour sur `days` jours finissant à `end_date`.

    Hypothèse : `total_balance` = solde réel à `end_date`. On remonte le temps
    en soustrayant les flux nets quotidiens strictement postérieurs à chaque
    date. C'est une estimation — les weekends/jours sans mouvement gardent la
    valeur du jour précédent, les transactions hors période ne sont pas prises
    en compte. Suffisant pour une tendance visuelle.
    """
    start_date = end_date - timedelta(days=days - 1)

    rows = db.execute(
        select(
            Transaction.operation_date.label("d"),
            func.coalesce(func.sum(Transaction.amount), 0).label("net"),
        )
        .where(
            and_(
                Transaction.bank_account_id.in_(bank_account_ids),
                Transaction.operation_date >= start_date,
                Transaction.operation_date <= end_date,
                Transaction.is_aggregation_parent.is_(False),
            )
        )
        .group_by(Transaction.operation_date)
        .order_by(Transaction.operation_date)
    ).all()

    net_by_day: dict[date, Decimal] = {r.d: Decimal(r.net) for r in rows}

    # On calcule d'abord le solde en fin de journée pour chaque date entre
    # start_date et end_date, en partant de total_balance et en remontant.
    balance_by_day: dict[date, Decimal] = {}
    running = total_balance
    cur = end_date
    while cur >= start_date:
        balance_by_day[cur] = running
        running = running - net_by_day.get(cur, Decimal("0"))
        cur = cur - timedelta(days=1)

    return [
        DailyBalance(date=d, balance=balance_by_day[d])
        for d in sorted(balance_by_day)
    ]


def _compute_total_balance(
    db: Session, bank_account_ids: list[int]
) -> tuple[Decimal, date | None]:
    """Σ des closing_balance du dernier ImportRecord COMPLETED par compte."""
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
            ImportRecord.closing_balance,
            ImportRecord.period_end,
        )
        .join(
            latest_per_account,
            and_(
                ImportRecord.bank_account_id == latest_per_account.c.bank_account_id,
                ImportRecord.period_end == latest_per_account.c.last_end,
            ),
        )
    ).all()

    total = sum((r.closing_balance for r in rows), Decimal("0"))
    max_date = max((r.period_end for r in rows if r.period_end), default=None)
    return total, max_date
