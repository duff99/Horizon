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
from app.models.category import Category
from app.models.counterparty import Counterparty
from app.models.entity import Entity
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction, TransactionCategorizationSource
from app.models.user import User
from app.models.user_entity_access import UserEntityAccess
from app.schemas.dashboard import (
    Alert,
    AlertSeverity,
    BankAccountBalance,
    CategoryBreakdown,
    CategoryBreakdownItem,
    DailyBalance,
    DailyCashflow,
    DashboardPeriod,
    DashboardSummary,
    MonthComparison,
    MonthComparisonPoint,
    TopCounterparties,
    TopCounterpartyItem,
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

_FR_MONTHS = (
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
)

_FR_MONTHS_ABBR = (
    "janv.", "févr.", "mars", "avr.", "mai", "juin",
    "juil.", "août", "sept.", "oct.", "nov.", "déc.",
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


def _resolve_range(
    period: DashboardPeriod,
    date_from: date | None,
    date_to: date | None,
    today: date,
) -> tuple[date, date, str]:
    """Résout la plage effective.

    Si `date_from` et `date_to` sont fournis, ils priment sur `period` et
    on retourne un label lisible (plage personnalisée).
    Sinon, on utilise la logique enum historique.
    """
    if date_from is not None and date_to is not None:
        label = f"{date_from.strftime('%d/%m/%Y')} → {date_to.strftime('%d/%m/%Y')}"
        return date_from, date_to, label
    return _resolve_period(period, today)


@router.get("/summary", response_model=DashboardSummary)
def get_summary(
    period: DashboardPeriod = Query(DashboardPeriod.CURRENT_MONTH),
    entity_id: int | None = Query(None),
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardSummary:
    today = date.today()
    period_start, period_end, period_label = _resolve_range(
        period, date_from, date_to, today
    )

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


def _resolve_accessible_bank_accounts(
    db: Session, *, user: User, entity_id: int | None,
) -> list[int]:
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
    return list(db.scalars(select(BankAccount.id).where(and_(*entity_filter))))


@router.get("/bank-balances", response_model=list[BankAccountBalance])
def get_bank_balances(
    entity_id: int | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[BankAccountBalance]:
    """Solde par compte bancaire + Δ vs mois précédent + date du dernier import."""
    bank_account_ids = _resolve_accessible_bank_accounts(
        db, user=user, entity_id=entity_id,
    )
    if not bank_account_ids:
        return []

    accounts = db.execute(
        select(BankAccount, Entity.name.label("entity_name"))
        .join(Entity, Entity.id == BankAccount.entity_id)
        .where(BankAccount.id.in_(bank_account_ids))
        .order_by(Entity.name, BankAccount.bank_name, BankAccount.name)
    ).all()

    # Dernier closing_balance par compte
    latest_per_account = (
        select(
            ImportRecord.bank_account_id.label("ba_id"),
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
        )
        .join(
            latest_per_account,
            and_(
                ImportRecord.bank_account_id == latest_per_account.c.ba_id,
                ImportRecord.period_end == latest_per_account.c.last_end,
            ),
        )
    ).all()
    latest_by_ba: dict[int, tuple[Decimal, date]] = {
        r.bank_account_id: (Decimal(r.closing_balance), r.period_end)
        for r in latest_rows
    }

    # Dernière date d'import (status COMPLETED) par compte — peut différer de period_end
    last_import_rows = db.execute(
        select(
            ImportRecord.bank_account_id,
            func.max(ImportRecord.created_at).label("last_at"),
        )
        .where(
            and_(
                ImportRecord.bank_account_id.in_(bank_account_ids),
                ImportRecord.status == ImportStatus.COMPLETED,
            )
        )
        .group_by(ImportRecord.bank_account_id)
    ).all()
    last_import_by_ba: dict[int, date] = {
        r.bank_account_id: r.last_at.date() if r.last_at else None
        for r in last_import_rows
    }

    # Δ vs mois précédent : solde actuel - solde du dernier import dont period_end < début du mois courant
    today = date.today()
    first_of_month = today.replace(day=1)
    prev_rows = db.execute(
        select(
            ImportRecord.bank_account_id,
            func.max(ImportRecord.period_end).label("last_end"),
        )
        .where(
            and_(
                ImportRecord.bank_account_id.in_(bank_account_ids),
                ImportRecord.status == ImportStatus.COMPLETED,
                ImportRecord.closing_balance.is_not(None),
                ImportRecord.period_end < first_of_month,
            )
        )
        .group_by(ImportRecord.bank_account_id)
    ).all()
    prev_end_by_ba = {r.bank_account_id: r.last_end for r in prev_rows}
    prev_balance_rows = db.execute(
        select(
            ImportRecord.bank_account_id,
            ImportRecord.closing_balance,
        ).where(
            and_(
                ImportRecord.bank_account_id.in_(prev_end_by_ba.keys()),
                ImportRecord.period_end.in_(prev_end_by_ba.values()),
                ImportRecord.status == ImportStatus.COMPLETED,
            )
        )
    ).all() if prev_end_by_ba else []
    prev_balance_by_ba: dict[int, Decimal] = {
        r.bank_account_id: Decimal(r.closing_balance)
        for r in prev_balance_rows
        if prev_end_by_ba.get(r.bank_account_id)
    }

    out: list[BankAccountBalance] = []
    for ba, entity_name in accounts:
        current = latest_by_ba.get(ba.id)
        balance = current[0] if current else Decimal("0")
        asof = current[1] if current else None
        prev = prev_balance_by_ba.get(ba.id)
        delta = balance - prev if prev is not None else None
        out.append(
            BankAccountBalance(
                bank_account_id=ba.id,
                entity_id=ba.entity_id,
                entity_name=entity_name,
                bank_name=ba.bank_name,
                account_name=ba.name,
                balance=balance,
                asof=asof,
                delta_vs_prev_month=delta,
                last_import_at=last_import_by_ba.get(ba.id),
            )
        )
    return out


@router.get("/categories", response_model=CategoryBreakdown)
def get_category_breakdown(
    period: DashboardPeriod = Query(DashboardPeriod.CURRENT_MONTH),
    entity_id: int | None = Query(None),
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CategoryBreakdown:
    """Répartition des flux par catégorie (top 5 + 'Autres') sur la période."""
    bank_account_ids = _resolve_accessible_bank_accounts(
        db, user=user, entity_id=entity_id,
    )
    if not bank_account_ids:
        return CategoryBreakdown(income=[], expense=[])

    today = date.today()
    period_start, period_end, _ = _resolve_range(period, date_from, date_to, today)

    base_where = and_(
        Transaction.bank_account_id.in_(bank_account_ids),
        Transaction.operation_date >= period_start,
        Transaction.operation_date <= period_end,
        Transaction.is_aggregation_parent.is_(False),
    )

    rows = db.execute(
        select(
            Transaction.category_id,
            Category.name,
            Category.color,
            func.sum(
                case((Transaction.amount > 0, Transaction.amount), else_=0)
            ).label("inflow"),
            func.sum(
                case((Transaction.amount < 0, Transaction.amount), else_=0)
            ).label("outflow"),
        )
        .select_from(Transaction)
        .outerjoin(Category, Category.id == Transaction.category_id)
        .where(base_where)
        .group_by(Transaction.category_id, Category.name, Category.color)
    ).all()

    income_raw: list[tuple[int | None, str, str | None, Decimal]] = []
    expense_raw: list[tuple[int | None, str, str | None, Decimal]] = []
    for r in rows:
        name = r.name or "Non catégorisé"
        if r.inflow and Decimal(r.inflow) > 0:
            income_raw.append((r.category_id, name, r.color, Decimal(r.inflow)))
        if r.outflow and Decimal(r.outflow) < 0:
            expense_raw.append(
                (r.category_id, name, r.color, abs(Decimal(r.outflow)))
            )

    return CategoryBreakdown(
        income=_top_n_with_others(income_raw, 5),
        expense=_top_n_with_others(expense_raw, 5),
    )


def _top_n_with_others(
    rows: list[tuple[int | None, str, str | None, Decimal]],
    n: int,
) -> list[CategoryBreakdownItem]:
    rows = sorted(rows, key=lambda r: r[3], reverse=True)
    total = sum((r[3] for r in rows), Decimal("0"))
    if total == 0:
        return []
    top = rows[:n]
    rest = rows[n:]
    out = [
        CategoryBreakdownItem(
            category_id=cid,
            name=name,
            color=color,
            amount=amount,
            pct=float(amount / total * 100),
        )
        for cid, name, color, amount in top
    ]
    if rest:
        rest_sum = sum((r[3] for r in rest), Decimal("0"))
        out.append(
            CategoryBreakdownItem(
                category_id=None,
                name="Autres",
                color=None,
                amount=rest_sum,
                pct=float(rest_sum / total * 100),
            )
        )
    return out


@router.get("/top-counterparties", response_model=TopCounterparties)
def get_top_counterparties(
    period: DashboardPeriod = Query(DashboardPeriod.CURRENT_MONTH),
    entity_id: int | None = Query(None),
    limit: int = Query(5, ge=1, le=20),
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TopCounterparties:
    """Top N contreparties en encaissements / décaissements sur la période."""
    bank_account_ids = _resolve_accessible_bank_accounts(
        db, user=user, entity_id=entity_id,
    )
    if not bank_account_ids:
        return TopCounterparties(top_inflows=[], top_outflows=[])

    today = date.today()
    period_start, period_end, _ = _resolve_range(period, date_from, date_to, today)

    base_where = and_(
        Transaction.bank_account_id.in_(bank_account_ids),
        Transaction.operation_date >= period_start,
        Transaction.operation_date <= period_end,
        Transaction.is_aggregation_parent.is_(False),
    )

    def _query(is_inflow: bool) -> list[TopCounterpartyItem]:
        amount_cond = Transaction.amount > 0 if is_inflow else Transaction.amount < 0
        rows = db.execute(
            select(
                Transaction.counterparty_id,
                Counterparty.name,
                func.sum(Transaction.amount).label("total"),
                func.count().label("n"),
            )
            .select_from(Transaction)
            .outerjoin(Counterparty, Counterparty.id == Transaction.counterparty_id)
            .where(and_(base_where, amount_cond))
            .group_by(Transaction.counterparty_id, Counterparty.name)
            .order_by(
                (func.sum(Transaction.amount) if is_inflow else -func.sum(Transaction.amount)).desc()
            )
            .limit(limit)
        ).all()
        return [
            TopCounterpartyItem(
                counterparty_id=r.counterparty_id,
                name=r.name or "Non attribué",
                amount=abs(Decimal(r.total)),
                transactions_count=int(r.n),
            )
            for r in rows
        ]

    return TopCounterparties(
        top_inflows=_query(is_inflow=True),
        top_outflows=_query(is_inflow=False),
    )


@router.get("/alerts", response_model=list[Alert])
def get_alerts(
    entity_id: int | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Alert]:
    """Alertes opérationnelles : soldes critiques, imports obsolètes, non catégorisées."""
    bank_account_ids = _resolve_accessible_bank_accounts(
        db, user=user, entity_id=entity_id,
    )
    if not bank_account_ids:
        return []

    alerts: list[Alert] = []
    today = date.today()

    # Alerte 1 : compte dont le dernier closing_balance est négatif
    balances = get_bank_balances(entity_id=entity_id, user=user, db=db)
    for b in balances:
        if b.balance < 0:
            alerts.append(
                Alert(
                    id=f"neg-balance-{b.bank_account_id}",
                    severity=AlertSeverity.CRITICAL,
                    title=f"Solde négatif sur {b.account_name}",
                    detail=f"{b.entity_name} — {b.balance} € au {b.asof.isoformat() if b.asof else '?'}",
                    entity_id=b.entity_id,
                    bank_account_id=b.bank_account_id,
                )
            )
        if b.last_import_at and (today - b.last_import_at).days > 35:
            age = (today - b.last_import_at).days
            alerts.append(
                Alert(
                    id=f"stale-{b.bank_account_id}",
                    severity=AlertSeverity.WARNING,
                    title=f"Aucun import récent — {b.account_name}",
                    detail=f"{b.entity_name} — dernier import il y a {age} jours",
                    entity_id=b.entity_id,
                    bank_account_id=b.bank_account_id,
                )
            )

    # Alerte 2 : transactions non catégorisées (seuil 20)
    uncategorized_count = db.execute(
        select(func.count())
        .select_from(Transaction)
        .where(
            and_(
                Transaction.bank_account_id.in_(bank_account_ids),
                Transaction.is_aggregation_parent.is_(False),
                Transaction.categorized_by == TransactionCategorizationSource.NONE,
            )
        )
    ).scalar_one()
    if uncategorized_count >= 20:
        alerts.append(
            Alert(
                id="uncategorized-many",
                severity=AlertSeverity.WARNING,
                title=f"{uncategorized_count} transactions à catégoriser",
                detail="Créez des règles ou catégorisez manuellement pour enrichir le tableau de bord.",
                entity_id=entity_id,
            )
        )

    # Alerte 3 : entrées prévisionnelles dont la due_date est passée et pas récurrente
    from app.models.forecast_entry import ForecastEntry, ForecastRecurrence

    accessible = list(
        db.scalars(
            select(UserEntityAccess.entity_id).where(
                UserEntityAccess.user_id == user.id
            )
        )
    )
    forecast_where = [
        ForecastEntry.due_date < today,
        ForecastEntry.recurrence == ForecastRecurrence.NONE,
    ]
    if entity_id is not None:
        forecast_where.append(ForecastEntry.entity_id == entity_id)
    else:
        forecast_where.append(ForecastEntry.entity_id.in_(accessible))
    stale_entries = db.execute(
        select(func.count()).select_from(ForecastEntry).where(and_(*forecast_where))
    ).scalar_one()
    if stale_entries > 0:
        alerts.append(
            Alert(
                id="stale-forecast",
                severity=AlertSeverity.INFO,
                title=f"{stale_entries} entrée(s) prévisionnelle(s) dépassée(s)",
                detail="Pensez à les supprimer ou les rapprocher d'une transaction réelle.",
                entity_id=entity_id,
            )
        )

    return alerts


def _month_range(first_of: date) -> tuple[date, date]:
    """Retourne (premier jour, dernier jour) du mois contenant `first_of`."""
    last_day = calendar.monthrange(first_of.year, first_of.month)[1]
    return first_of, date(first_of.year, first_of.month, last_day)


def _previous_first(first_of: date) -> date:
    if first_of.month == 1:
        return date(first_of.year - 1, 12, 1)
    return date(first_of.year, first_of.month - 1, 1)


@router.get("/month-comparison", response_model=MonthComparison)
def get_month_comparison(
    entity_id: int | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MonthComparison:
    """Comparaison in/out du mois courant vs mois précédent (en centimes)."""
    bank_account_ids = _resolve_accessible_bank_accounts(
        db, user=user, entity_id=entity_id,
    )
    today = date.today()
    current_first = today.replace(day=1)
    previous_first = _previous_first(current_first)

    current_label = f"{_FR_MONTHS_ABBR[current_first.month - 1]} {current_first.year}"
    previous_label = f"{_FR_MONTHS_ABBR[previous_first.month - 1]} {previous_first.year}"

    if not bank_account_ids:
        return MonthComparison(
            current=MonthComparisonPoint(
                month_label=current_label, in_cents=0, out_cents=0
            ),
            previous=MonthComparisonPoint(
                month_label=previous_label, in_cents=0, out_cents=0
            ),
        )

    def _totals(month_first: date) -> tuple[int, int]:
        month_start, month_end = _month_range(month_first)
        row = db.execute(
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
                    Transaction.operation_date >= month_start,
                    Transaction.operation_date <= month_end,
                    Transaction.is_aggregation_parent.is_(False),
                )
            )
        ).one()
        # Conversion Decimal euros → centimes int.
        in_cents = int((Decimal(row.inflows) * 100).to_integral_value())
        out_cents = int((Decimal(row.outflows) * 100).to_integral_value())
        return in_cents, out_cents

    cur_in, cur_out = _totals(current_first)
    prev_in, prev_out = _totals(previous_first)

    return MonthComparison(
        current=MonthComparisonPoint(
            month_label=current_label, in_cents=cur_in, out_cents=cur_out
        ),
        previous=MonthComparisonPoint(
            month_label=previous_label, in_cents=prev_in, out_cents=prev_out
        ),
    )
