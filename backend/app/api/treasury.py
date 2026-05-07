"""Endpoints trésorerie — G1 (solde quotidien 90j) et G10 (position par compte)."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import accessible_entity_ids_subquery, get_current_user, require_entity_access
from app.models.bank_account import BankAccount
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.treasury import (
    DailyBalancePoint,
    DailyBalanceResponse,
    PerAccountBalance,
    PerAccountBalanceResponse,
)
from app.services._anchor import data_anchor

router = APIRouter(prefix="/api/treasury", tags=["treasury"])


# ---------------------------------------------------------------------------
# Helpers partagés (répliqués depuis dashboard.py pour encapsulation)
# ---------------------------------------------------------------------------

def _resolve_bank_accounts_for_entity(
    db: Session,
    *,
    user: User,
    entity_id: int,
) -> list[int]:
    """Retourne les bank_account_ids accessibles pour entity_id (vérifie 403)."""
    require_entity_access(session=db, user=user, entity_id=entity_id)
    return list(
        db.scalars(
            select(BankAccount.id).where(BankAccount.entity_id == entity_id)
        )
    )


def _compute_total_balance_for_accounts(
    db: Session, bank_account_ids: list[int]
) -> tuple[Decimal, date | None]:
    """Σ closing_balance du dernier ImportRecord COMPLETED par compte."""
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
        ).join(
            latest_per_account,
            and_(
                ImportRecord.bank_account_id == latest_per_account.c.bank_account_id,
                ImportRecord.period_end == latest_per_account.c.last_end,
            ),
        )
    ).all()
    total = sum((Decimal(r.closing_balance) for r in rows), Decimal("0"))
    max_date = max((r.period_end for r in rows if r.period_end), default=None)
    return total, max_date


def _compute_balance_trend_for_accounts(
    db: Session,
    *,
    bank_account_ids: list[int],
    total_balance: Decimal,
    end_date: date,
    days: int,
) -> list[DailyBalancePoint]:
    """Reconstruit le solde estimé jour par jour sur `days` jours finissant à `end_date`."""
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

    balance_by_day: dict[date, Decimal] = {}
    running = total_balance
    cur = end_date
    while cur >= start_date:
        balance_by_day[cur] = running
        running = running - net_by_day.get(cur, Decimal("0"))
        cur = cur - timedelta(days=1)

    return [
        DailyBalancePoint(date=d, balance=balance_by_day[d])
        for d in sorted(balance_by_day)
    ]


# ---------------------------------------------------------------------------
# G1 — GET /api/treasury/daily-balance
# ---------------------------------------------------------------------------

@router.get("/daily-balance", response_model=DailyBalanceResponse)
def get_daily_balance(
    entity_id: int = Query(...),
    days: int = Query(90, ge=7, le=365),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DailyBalanceResponse:
    """Solde de trésorerie reconstruit jour par jour sur `days` jours (G1)."""
    bank_account_ids = _resolve_bank_accounts_for_entity(
        db, user=user, entity_id=entity_id
    )

    if not bank_account_ids:
        return DailyBalanceResponse(
            entity_id=entity_id,
            days=days,
            points=[],
            latest_balance=None,
            latest_date=None,
        )

    total_balance, last_date = _compute_total_balance_for_accounts(db, bank_account_ids)

    if last_date is None:
        return DailyBalanceResponse(
            entity_id=entity_id,
            days=days,
            points=[],
            latest_balance=None,
            latest_date=None,
        )

    points = _compute_balance_trend_for_accounts(
        db,
        bank_account_ids=bank_account_ids,
        total_balance=total_balance,
        end_date=last_date,
        days=days,
    )

    return DailyBalanceResponse(
        entity_id=entity_id,
        days=days,
        points=points,
        latest_balance=total_balance,
        latest_date=last_date,
    )


# ---------------------------------------------------------------------------
# G10 — GET /api/treasury/per-account
# ---------------------------------------------------------------------------

@router.get("/per-account", response_model=PerAccountBalanceResponse)
def get_per_account(
    entity_id: int | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PerAccountBalanceResponse:
    """Position de trésorerie nette par compte bancaire avec sparkline 30j (G10)."""
    # Résoudre les bank_account_ids accessibles
    if entity_id is not None:
        require_entity_access(session=db, user=user, entity_id=entity_id)
        bank_account_ids = list(
            db.scalars(
                select(BankAccount.id).where(BankAccount.entity_id == entity_id)
            )
        )
    else:
        accessible_ids = list(
            db.scalars(accessible_entity_ids_subquery(session=db, user=user))
        )
        bank_account_ids = list(
            db.scalars(
                select(BankAccount.id).where(BankAccount.entity_id.in_(accessible_ids))
            )
        )

    if not bank_account_ids:
        return PerAccountBalanceResponse(entity_id=entity_id, accounts=[])

    # Charger les infos des comptes
    accounts = db.execute(
        select(BankAccount).where(BankAccount.id.in_(bank_account_ids))
    ).scalars().all()

    # Dernier closing_balance par compte (solde courant)
    latest_per_account_sq = (
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
    latest_rows = db.execute(
        select(
            ImportRecord.bank_account_id,
            ImportRecord.closing_balance,
            ImportRecord.period_end,
        ).join(
            latest_per_account_sq,
            and_(
                ImportRecord.bank_account_id == latest_per_account_sq.c.bank_account_id,
                ImportRecord.period_end == latest_per_account_sq.c.last_end,
            ),
        )
    ).all()
    latest_by_ba: dict[int, tuple[Decimal, date]] = {
        r.bank_account_id: (Decimal(r.closing_balance), r.period_end)
        for r in latest_rows
    }

    # Solde il y a 30 jours : dernier closing_balance dont period_end <= anchor - 30
    today = data_anchor(db, entity_id=entity_id)
    cutoff_30d = today - timedelta(days=30)
    prev30_sq = (
        select(
            ImportRecord.bank_account_id,
            func.max(ImportRecord.period_end).label("last_end"),
        )
        .where(
            and_(
                ImportRecord.bank_account_id.in_(bank_account_ids),
                ImportRecord.status == ImportStatus.COMPLETED,
                ImportRecord.closing_balance.is_not(None),
                ImportRecord.period_end <= cutoff_30d,
            )
        )
        .group_by(ImportRecord.bank_account_id)
        .subquery()
    )
    prev30_rows = db.execute(
        select(
            ImportRecord.bank_account_id,
            ImportRecord.closing_balance,
        ).join(
            prev30_sq,
            and_(
                ImportRecord.bank_account_id == prev30_sq.c.bank_account_id,
                ImportRecord.period_end == prev30_sq.c.last_end,
            ),
        )
    ).all()
    prev30_by_ba: dict[int, Decimal] = {
        r.bank_account_id: Decimal(r.closing_balance)
        for r in prev30_rows
    }

    # Date du dernier import COMPLETED par compte
    last_import_rows = db.execute(
        select(
            ImportRecord.bank_account_id,
            func.max(ImportRecord.period_end).label("last_end"),
        )
        .where(
            and_(
                ImportRecord.bank_account_id.in_(bank_account_ids),
                ImportRecord.status == ImportStatus.COMPLETED,
            )
        )
        .group_by(ImportRecord.bank_account_id)
    ).all()
    last_import_by_ba: dict[int, date | None] = {
        r.bank_account_id: r.last_end for r in last_import_rows
    }

    result: list[PerAccountBalance] = []
    for ba in accounts:
        current_info = latest_by_ba.get(ba.id)
        if current_info is None:
            current_balance = Decimal("0")
            last_import_date = last_import_by_ba.get(ba.id)
        else:
            current_balance, last_import_date = current_info

        balance_cents = int(current_balance * 100)

        prev30 = prev30_by_ba.get(ba.id)
        balance_30d_ago_cents = int(prev30 * 100) if prev30 is not None else None
        variation_30d_cents = (
            balance_cents - balance_30d_ago_cents
            if balance_30d_ago_cents is not None
            else None
        )

        # Sparkline : 30 points quotidiens via reconstruction à rebours
        sparkline_points = _compute_balance_trend_for_accounts(
            db,
            bank_account_ids=[ba.id],
            total_balance=current_balance,
            end_date=last_import_date if last_import_date else today,
            days=30,
        )
        sparkline = [int(p.balance * 100) for p in sparkline_points]

        iban_last4 = ba.iban[-4:] if ba.iban and len(ba.iban) >= 4 else ba.iban or ""

        result.append(
            PerAccountBalance(
                account_id=ba.id,
                account_name=ba.name,
                bank_name=ba.bank_name,
                iban_last4=iban_last4,
                balance_cents=balance_cents,
                balance_30d_ago_cents=balance_30d_ago_cents,
                variation_30d_cents=variation_30d_cents,
                last_import_date=last_import_date,
                sparkline=sparkline,
            )
        )

    return PerAccountBalanceResponse(entity_id=entity_id, accounts=result)
