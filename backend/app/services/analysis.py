"""Logique métier pour les endpoints `/api/analysis/*`.

Chaque fonction prend une session SQLAlchemy + les paramètres de l'endpoint et
retourne un objet Pydantic prêt à être renvoyé. Les montants sont en centimes
(int) pour éviter les arrondis flottants.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Iterable

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.deps import accessible_entity_ids_subquery
from app.models.bank_account import BankAccount
from app.models.category import Category
from app.models.commitment import (
    Commitment,
    CommitmentDirection,
    CommitmentStatus,
)
from app.models.counterparty import Counterparty
from app.models.entity import Entity
from app.models.forecast_entry import ForecastEntry
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.analysis import (
    CategoryDriftResponse,
    CategoryDriftRow,
    ClientConcentrationResponse,
    ClientSlice,
    EntitiesComparisonResponse,
    EntityCompareRow,
    ForecastVariancePoint,
    ForecastVarianceResponse,
    RunwayResponse,
    TopMoverRow,
    TopMoversResponse,
    WorkingCapitalResponse,
    YoYPoint,
    YoYResponse,
)


# ---------------------------------------------------------------------------
# Helpers date / mois
# ---------------------------------------------------------------------------


def _first_of_month(d: date) -> date:
    return d.replace(day=1)


def _add_months(d: date, months: int) -> date:
    d = _first_of_month(d)
    total = d.year * 12 + (d.month - 1) + months
    year, month_idx = divmod(total, 12)
    return date(year, month_idx + 1, 1)


def _month_key(d: date) -> str:
    return d.strftime("%Y-%m")


def _eur_to_cents(amount: Decimal | float | int | None) -> int:
    if amount is None:
        return 0
    return int((Decimal(amount) * Decimal(100)).to_integral_value())


def _bank_account_ids_for_entity(session: Session, entity_id: int) -> list[int]:
    return list(
        session.scalars(
            select(BankAccount.id).where(BankAccount.entity_id == entity_id)
        )
    )


def _accessible_entity_ids(session: Session, user: User) -> list[int]:
    return list(
        session.scalars(accessible_entity_ids_subquery(session=session, user=user))
    )


# ---------------------------------------------------------------------------
# 1. Category drift
# ---------------------------------------------------------------------------


def compute_category_drift(
    session: Session, *, entity_id: int, seuil_pct: float,
) -> CategoryDriftResponse:
    """Compare chaque catégorie : mois courant vs moyenne 3 mois précédents."""
    today = date.today()
    current_first = _first_of_month(today)
    prev1 = _add_months(current_first, -1)
    earliest = _add_months(current_first, -3)
    latest = _add_months(current_first, 1)  # exclusive

    ba_ids = _bank_account_ids_for_entity(session, entity_id)
    if not ba_ids:
        return CategoryDriftResponse(rows=[], seuil_pct=seuil_pct)

    month_col = func.date_trunc("month", Transaction.operation_date)
    rows = session.execute(
        select(
            Transaction.category_id,
            Category.name,
            month_col.label("month"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .join(Category, Category.id == Transaction.category_id)
        .where(
            and_(
                Transaction.bank_account_id.in_(ba_ids),
                Transaction.operation_date >= earliest,
                Transaction.operation_date < latest,
                Transaction.is_aggregation_parent.is_(False),
                Transaction.category_id.is_not(None),
            )
        )
        .group_by(Transaction.category_id, Category.name, month_col)
    ).all()

    # cat_id -> {month_key: cents}
    by_cat: dict[int, dict[str, int]] = defaultdict(dict)
    labels: dict[int, str] = {}
    for cat_id, name, month, total in rows:
        if cat_id is None or month is None:
            continue
        key = _month_key(month)
        by_cat[int(cat_id)][key] = _eur_to_cents(Decimal(total))
        labels[int(cat_id)] = name

    current_key = _month_key(current_first)
    prev_keys = [_month_key(_add_months(prev1, -i)) for i in range(0, 3)]

    out: list[CategoryDriftRow] = []
    for cat_id, months_map in by_cat.items():
        current = months_map.get(current_key, 0)
        prev_sum = sum(months_map.get(k, 0) for k in prev_keys)
        avg3m = prev_sum // 3 if prev_sum else 0
        # Skip si zéro partout : pas d'activité
        if current == 0 and avg3m == 0:
            continue
        delta = current - avg3m
        if avg3m == 0:
            delta_pct = 0.0
        else:
            delta_pct = (current - avg3m) / abs(avg3m) * 100.0
        status = "alert" if abs(delta_pct) > seuil_pct else "normal"
        out.append(
            CategoryDriftRow(
                category_id=cat_id,
                label=labels.get(cat_id, f"Catégorie {cat_id}"),
                current_cents=current,
                avg3m_cents=avg3m,
                delta_cents=delta,
                delta_pct=round(delta_pct, 2),
                status=status,
            )
        )

    out.sort(key=lambda r: abs(r.delta_pct), reverse=True)
    return CategoryDriftResponse(rows=out, seuil_pct=seuil_pct)


def compute_category_drift_detail(
    session: Session, *, entity_id: int, category_id: int,
):
    """Drill-down : transactions du mois courant pour une catégorie donnée.

    Utilisé par le clic sur une ligne du tableau Dérives par catégorie pour
    répondre à la question "à cause de quelles transactions exactement ?".
    Les transactions sont triées par montant absolu décroissant (les plus
    impactantes en premier).
    """
    from app.schemas.analysis import (
        CategoryDriftDetailResponse,
        CategoryDriftTransaction,
    )

    today = date.today()
    current_first = _first_of_month(today)
    next_first = _add_months(current_first, 1)

    ba_ids = _bank_account_ids_for_entity(session, entity_id)
    cat = session.get(Category, category_id)
    label = cat.name if cat else f"#{category_id}"

    if not ba_ids:
        return CategoryDriftDetailResponse(
            category_id=category_id,
            category_label=label,
            month=_month_key(current_first),
            total_cents=0,
            transactions=[],
        )

    rows = session.execute(
        select(
            Transaction.id,
            Transaction.operation_date,
            Transaction.label,
            Transaction.amount,
            Counterparty.name.label("counterparty_name"),
        )
        .outerjoin(Counterparty, Counterparty.id == Transaction.counterparty_id)
        .where(
            and_(
                Transaction.bank_account_id.in_(ba_ids),
                Transaction.category_id == category_id,
                Transaction.operation_date >= current_first,
                Transaction.operation_date < next_first,
                Transaction.is_aggregation_parent.is_(False),
            )
        )
        .order_by(func.abs(Transaction.amount).desc())
    ).all()

    transactions = [
        CategoryDriftTransaction(
            id=int(r.id),
            operation_date=r.operation_date.isoformat(),
            label=r.label or "",
            counterparty=r.counterparty_name,
            amount_cents=_eur_to_cents(Decimal(r.amount)),
        )
        for r in rows
    ]
    total = sum(t.amount_cents for t in transactions)

    return CategoryDriftDetailResponse(
        category_id=category_id,
        category_label=label,
        month=_month_key(current_first),
        total_cents=total,
        transactions=transactions,
    )


# ---------------------------------------------------------------------------
# 2. Top movers
# ---------------------------------------------------------------------------


def compute_top_movers(
    session: Session, *, entity_id: int, limit: int,
) -> TopMoversResponse:
    """Top N catégories par |delta vs mois précédent| avec sparkline 3m."""
    today = date.today()
    current_first = _first_of_month(today)
    # On récupère 4 mois : courant + 3 précédents (pour sparkline 3m et delta)
    # Sparkline = [m-3, m-2, m-1] (3 derniers mois finis), delta = current - (m-1)
    earliest = _add_months(current_first, -3)
    latest = _add_months(current_first, 1)  # exclusive (inclut mois courant)

    ba_ids = _bank_account_ids_for_entity(session, entity_id)
    if not ba_ids:
        return TopMoversResponse(increases=[], decreases=[])

    month_col = func.date_trunc("month", Transaction.operation_date)
    rows = session.execute(
        select(
            Transaction.category_id,
            Category.name,
            month_col.label("month"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
            # Somme des amounts positifs pour détecter direction
            func.coalesce(
                func.sum(
                    case((Transaction.amount > 0, Transaction.amount), else_=0)
                ),
                0,
            ).label("pos"),
            func.coalesce(
                func.sum(
                    case((Transaction.amount < 0, Transaction.amount), else_=0)
                ),
                0,
            ).label("neg"),
        )
        .join(Category, Category.id == Transaction.category_id)
        .where(
            and_(
                Transaction.bank_account_id.in_(ba_ids),
                Transaction.operation_date >= earliest,
                Transaction.operation_date < latest,
                Transaction.is_aggregation_parent.is_(False),
                Transaction.category_id.is_not(None),
            )
        )
        .group_by(Transaction.category_id, Category.name, month_col)
    ).all()

    by_cat: dict[int, dict[str, int]] = defaultdict(dict)
    labels: dict[int, str] = {}
    direction_totals: dict[int, tuple[Decimal, Decimal]] = defaultdict(
        lambda: (Decimal(0), Decimal(0))
    )
    for cat_id, name, month, total, pos, neg in rows:
        if cat_id is None or month is None:
            continue
        key = _month_key(month)
        by_cat[int(cat_id)][key] = _eur_to_cents(Decimal(total))
        labels[int(cat_id)] = name
        p, n = direction_totals[int(cat_id)]
        direction_totals[int(cat_id)] = (p + Decimal(pos), n + Decimal(neg))

    current_key = _month_key(current_first)
    prev_key = _month_key(_add_months(current_first, -1))
    # 3 derniers mois finis = [m-3, m-2, m-1]
    spark_keys = [_month_key(_add_months(current_first, -3 + i)) for i in range(3)]

    candidates: list[TopMoverRow] = []
    for cat_id, months_map in by_cat.items():
        current = months_map.get(current_key, 0)
        prev = months_map.get(prev_key, 0)
        delta = current - prev
        if delta == 0:
            continue
        pos_total, neg_total = direction_totals[cat_id]
        direction = "in" if pos_total >= abs(neg_total) else "out"
        sparkline = [months_map.get(k, 0) for k in spark_keys]
        candidates.append(
            TopMoverRow(
                category_id=cat_id,
                label=labels.get(cat_id, f"Catégorie {cat_id}"),
                direction=direction,
                delta_cents=delta,
                sparkline_3m_cents=sparkline,
            )
        )

    increases = sorted(
        [c for c in candidates if c.delta_cents > 0],
        key=lambda r: r.delta_cents,
        reverse=True,
    )[:limit]
    decreases = sorted(
        [c for c in candidates if c.delta_cents < 0],
        key=lambda r: r.delta_cents,
    )[:limit]
    return TopMoversResponse(increases=increases, decreases=decreases)


# ---------------------------------------------------------------------------
# 3. Runway
# ---------------------------------------------------------------------------


def _monthly_net_cents(
    session: Session, *, ba_ids: list[int], from_month: date, to_month: date,
) -> dict[str, int]:
    """Somme signée (in + out) par mois sur [from_month, to_month) (exclusive)."""
    if not ba_ids:
        return {}
    month_col = func.date_trunc("month", Transaction.operation_date)
    rows = session.execute(
        select(
            month_col.label("month"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .where(
            and_(
                Transaction.bank_account_id.in_(ba_ids),
                Transaction.operation_date >= from_month,
                Transaction.operation_date < to_month,
                Transaction.is_aggregation_parent.is_(False),
            )
        )
        .group_by(month_col)
    ).all()
    out: dict[str, int] = {}
    for month, total in rows:
        if month is None:
            continue
        out[_month_key(month)] = _eur_to_cents(Decimal(total))
    return out


def _current_balance_cents(session: Session, ba_ids: list[int]) -> int:
    """Σ closing_balance du dernier ImportRecord COMPLETED par compte."""
    if not ba_ids:
        return 0
    latest_per_account = (
        select(
            ImportRecord.bank_account_id,
            func.max(ImportRecord.period_end).label("last_end"),
        )
        .where(
            and_(
                ImportRecord.bank_account_id.in_(ba_ids),
                ImportRecord.status == ImportStatus.COMPLETED,
                ImportRecord.closing_balance.is_not(None),
                ImportRecord.period_end.is_not(None),
            )
        )
        .group_by(ImportRecord.bank_account_id)
        .subquery()
    )
    rows = session.execute(
        select(ImportRecord.closing_balance).join(
            latest_per_account,
            and_(
                ImportRecord.bank_account_id == latest_per_account.c.bank_account_id,
                ImportRecord.period_end == latest_per_account.c.last_end,
            ),
        )
    ).all()
    total = sum(
        (_eur_to_cents(Decimal(r.closing_balance)) for r in rows), 0
    )
    return total


def _compute_runway_core(
    session: Session, *, entity_id: int,
) -> tuple[int, int, int | None, list[int], str]:
    """Calcul runway core — retourne (burn, balance, months, forecast6, status).

    Utilisé à la fois par /runway et par /entities-comparison.
    """
    today = date.today()
    current_first = _first_of_month(today)
    # 3 derniers mois finis : [m-3, m-2, m-1]
    earliest = _add_months(current_first, -3)
    latest = current_first  # exclusive : ne pas inclure le mois courant

    ba_ids = _bank_account_ids_for_entity(session, entity_id)
    net_by_month = _monthly_net_cents(
        session, ba_ids=ba_ids, from_month=earliest, to_month=latest
    )
    months_3 = [
        _month_key(_add_months(current_first, -3 + i)) for i in range(3)
    ]
    values = [net_by_month.get(k, 0) for k in months_3]
    burn_rate = sum(values) // 3 if values else 0

    balance = _current_balance_cents(session, ba_ids)

    if burn_rate < 0:
        runway_months = abs(balance // burn_rate) if balance > 0 else 0
    else:
        runway_months = None

    # Projection 6 mois : balance + burn * (i+1)
    forecast = []
    running = balance
    for i in range(6):
        running += burn_rate
        forecast.append(running)

    if burn_rate >= 0:
        status = "none"
    elif runway_months is not None and runway_months < 3:
        status = "critical"
    elif runway_months is not None and runway_months < 6:
        status = "warning"
    else:
        status = "ok"

    return burn_rate, balance, runway_months, forecast, status


def compute_runway(session: Session, *, entity_id: int) -> RunwayResponse:
    burn_rate, balance, runway_months, forecast, status = _compute_runway_core(
        session, entity_id=entity_id
    )
    return RunwayResponse(
        burn_rate_cents=burn_rate,
        current_balance_cents=balance,
        runway_months=runway_months,
        forecast_balance_6m_cents=forecast,
        status=status,
    )


# ---------------------------------------------------------------------------
# 4. Year-over-year
# ---------------------------------------------------------------------------


def compute_yoy(session: Session, *, entity_id: int) -> YoYResponse:
    today = date.today()
    current_first = _first_of_month(today)
    # 12 mois glissants finissant au mois courant inclus
    months = [_add_months(current_first, -11 + i) for i in range(12)]
    # Plage : de 12m avant le plus ancien (pour année N-1) jusqu'au courant inclus
    earliest = _add_months(months[0], -12)
    latest = _add_months(current_first, 1)  # exclusive

    ba_ids = _bank_account_ids_for_entity(session, entity_id)
    if not ba_ids:
        month_keys = [_month_key(m) for m in months]
        return YoYResponse(
            months=month_keys,
            series=[
                YoYPoint(
                    month=k,
                    revenues_current=0,
                    revenues_previous=0,
                    expenses_current=0,
                    expenses_previous=0,
                )
                for k in month_keys
            ],
        )

    month_col = func.date_trunc("month", Transaction.operation_date)
    rows = session.execute(
        select(
            month_col.label("month"),
            func.coalesce(
                func.sum(
                    case((Transaction.amount > 0, Transaction.amount), else_=0)
                ),
                0,
            ).label("inflow"),
            func.coalesce(
                func.sum(
                    case((Transaction.amount < 0, Transaction.amount), else_=0)
                ),
                0,
            ).label("outflow"),
        )
        .where(
            and_(
                Transaction.bank_account_id.in_(ba_ids),
                Transaction.operation_date >= earliest,
                Transaction.operation_date < latest,
                Transaction.is_aggregation_parent.is_(False),
            )
        )
        .group_by(month_col)
    ).all()

    inflow_by_month: dict[str, int] = {}
    outflow_by_month: dict[str, int] = {}
    for month, inflow, outflow in rows:
        if month is None:
            continue
        k = _month_key(month)
        inflow_by_month[k] = _eur_to_cents(Decimal(inflow))
        outflow_by_month[k] = _eur_to_cents(Decimal(outflow))

    month_keys = [_month_key(m) for m in months]
    series: list[YoYPoint] = []
    for m in months:
        k = _month_key(m)
        k_prev = _month_key(_add_months(m, -12))
        series.append(
            YoYPoint(
                month=k,
                revenues_current=inflow_by_month.get(k, 0),
                revenues_previous=inflow_by_month.get(k_prev, 0),
                expenses_current=abs(outflow_by_month.get(k, 0)),
                expenses_previous=abs(outflow_by_month.get(k_prev, 0)),
            )
        )
    return YoYResponse(months=month_keys, series=series)


# ---------------------------------------------------------------------------
# 5. Client concentration
# ---------------------------------------------------------------------------


def compute_client_concentration(
    session: Session, *, entity_id: int, months: int,
) -> ClientConcentrationResponse:
    today = date.today()
    current_first = _first_of_month(today)
    earliest = _add_months(current_first, -(months - 1))
    latest = _add_months(current_first, 1)  # exclusive

    ba_ids = _bank_account_ids_for_entity(session, entity_id)
    if not ba_ids:
        return ClientConcentrationResponse(
            total_revenue_cents=0,
            top5=[],
            others_cents=0,
            others_share_pct=0.0,
            hhi=0.0,
            risk_level="low",
        )

    rows = session.execute(
        select(
            Transaction.counterparty_id,
            Counterparty.name,
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .join(Counterparty, Counterparty.id == Transaction.counterparty_id)
        .where(
            and_(
                Transaction.bank_account_id.in_(ba_ids),
                Transaction.operation_date >= earliest,
                Transaction.operation_date < latest,
                Transaction.is_aggregation_parent.is_(False),
                Transaction.counterparty_id.is_not(None),
                Transaction.amount > 0,
            )
        )
        .group_by(Transaction.counterparty_id, Counterparty.name)
    ).all()

    entries: list[tuple[int, str, int]] = [
        (int(r.counterparty_id), r.name, _eur_to_cents(Decimal(r.total)))
        for r in rows
        if Decimal(r.total) > 0
    ]
    total = sum(amount for _, _, amount in entries)
    if total == 0:
        return ClientConcentrationResponse(
            total_revenue_cents=0,
            top5=[],
            others_cents=0,
            others_share_pct=0.0,
            hhi=0.0,
            risk_level="low",
        )

    entries.sort(key=lambda e: e[2], reverse=True)
    top = entries[:5]
    rest = entries[5:]
    top5 = [
        ClientSlice(
            counterparty_id=cp_id,
            name=name,
            amount_cents=amount,
            share_pct=round(amount / total * 100.0, 2),
        )
        for cp_id, name, amount in top
    ]
    others = sum(amount for _, _, amount in rest)
    others_pct = round(others / total * 100.0, 2) if total else 0.0

    # HHI sur TOUS les tiers (pas seulement top5) — partie² × 10000
    hhi = 0.0
    for _, _, amount in entries:
        share = amount / total
        hhi += (share * 100.0) ** 2  # share en % : share²×10000
    hhi = round(hhi, 2)

    if hhi < 1500:
        risk_level = "low"
    elif hhi < 2500:
        risk_level = "medium"
    else:
        risk_level = "high"

    return ClientConcentrationResponse(
        total_revenue_cents=total,
        top5=top5,
        others_cents=others,
        others_share_pct=others_pct,
        hhi=hhi,
        risk_level=risk_level,
    )


# ---------------------------------------------------------------------------
# 6. Entities comparison
# ---------------------------------------------------------------------------


def compute_entities_comparison(
    session: Session, *, user: User, months: int,
) -> EntitiesComparisonResponse:
    entity_ids = _accessible_entity_ids(session, user)
    if not entity_ids:
        return EntitiesComparisonResponse(entities=[])

    today = date.today()
    current_first = _first_of_month(today)
    earliest = _add_months(current_first, -(months - 1))
    latest = _add_months(current_first, 1)  # exclusive

    entities = list(
        session.execute(
            select(Entity.id, Entity.name)
            .where(Entity.id.in_(entity_ids))
            .order_by(Entity.name)
        ).all()
    )

    out: list[EntityCompareRow] = []
    for e_id, name in entities:
        ba_ids = _bank_account_ids_for_entity(session, e_id)
        if not ba_ids:
            out.append(
                EntityCompareRow(
                    entity_id=e_id,
                    name=name,
                    revenues_cents=0,
                    expenses_cents=0,
                    net_variation_cents=0,
                    current_balance_cents=0,
                    burn_rate_cents=0,
                    runway_months=None,
                )
            )
            continue

        row = session.execute(
            select(
                func.coalesce(
                    func.sum(
                        case((Transaction.amount > 0, Transaction.amount), else_=0)
                    ),
                    0,
                ).label("inflow"),
                func.coalesce(
                    func.sum(
                        case((Transaction.amount < 0, Transaction.amount), else_=0)
                    ),
                    0,
                ).label("outflow"),
            ).where(
                and_(
                    Transaction.bank_account_id.in_(ba_ids),
                    Transaction.operation_date >= earliest,
                    Transaction.operation_date < latest,
                    Transaction.is_aggregation_parent.is_(False),
                )
            )
        ).one()
        revenues = _eur_to_cents(Decimal(row.inflow))
        expenses = abs(_eur_to_cents(Decimal(row.outflow)))
        net = revenues - expenses

        burn_rate, balance, runway_months, _forecast, _status = (
            _compute_runway_core(session, entity_id=e_id)
        )

        out.append(
            EntityCompareRow(
                entity_id=e_id,
                name=name,
                revenues_cents=revenues,
                expenses_cents=expenses,
                net_variation_cents=net,
                current_balance_cents=balance,
                burn_rate_cents=burn_rate,
                runway_months=runway_months,
            )
        )
    return EntitiesComparisonResponse(entities=out)


# ---------------------------------------------------------------------------
# 7. Forecast variance — réalisé vs prévisionnel
# ---------------------------------------------------------------------------


def compute_forecast_variance(
    session: Session, *, entity_id: int, months: int = 6,
) -> ForecastVarianceResponse:
    """Compare le réalisé (transactions) au prévisionnel (forecast_entries)
    sur les N derniers mois (mois courant inclus, défaut 6).

    Pour chaque mois :
      forecasted_cents = somme des forecast_entries.amount du mois
      actual_cents     = somme des Transaction.amount du mois
      delta            = actual - forecasted (signé)
      delta_pct        = delta / forecasted * 100, ou 0 si pas de prévu

    Renvoie has_forecast=False si aucune entrée prévisionnelle n'existe pour
    cette entité sur la fenêtre — l'UI affichera un état vide avec un
    call-to-action vers la page Prévisionnel.
    """
    today = date.today()
    current_first = _first_of_month(today)
    earliest = _add_months(current_first, -(months - 1))
    next_first = _add_months(current_first, 1)  # exclusive

    # Forecast aggregation par mois
    forecast_month = func.date_trunc("month", ForecastEntry.due_date)
    forecast_rows = session.execute(
        select(
            forecast_month.label("month"),
            func.coalesce(func.sum(ForecastEntry.amount), 0).label("total"),
        )
        .where(
            and_(
                ForecastEntry.entity_id == entity_id,
                ForecastEntry.due_date >= earliest,
                ForecastEntry.due_date < next_first,
            )
        )
        .group_by(forecast_month)
    ).all()
    forecast_by_month: dict[str, int] = {}
    for month, total in forecast_rows:
        if month is None:
            continue
        forecast_by_month[_month_key(month)] = _eur_to_cents(Decimal(total))

    # Actual aggregation par mois (depuis transactions)
    ba_ids = _bank_account_ids_for_entity(session, entity_id)
    actual_by_month: dict[str, int] = {}
    if ba_ids:
        actual_month = func.date_trunc("month", Transaction.operation_date)
        actual_rows = session.execute(
            select(
                actual_month.label("month"),
                func.coalesce(func.sum(Transaction.amount), 0).label("total"),
            )
            .where(
                and_(
                    Transaction.bank_account_id.in_(ba_ids),
                    Transaction.operation_date >= earliest,
                    Transaction.operation_date < next_first,
                    Transaction.is_aggregation_parent.is_(False),
                )
            )
            .group_by(actual_month)
        ).all()
        for month, total in actual_rows:
            if month is None:
                continue
            actual_by_month[_month_key(month)] = _eur_to_cents(Decimal(total))

    # Construit la série complète mois par mois
    points: list[ForecastVariancePoint] = []
    cursor = earliest
    while cursor < next_first:
        key = _month_key(cursor)
        forecasted = forecast_by_month.get(key, 0)
        actual = actual_by_month.get(key, 0)
        delta = actual - forecasted
        if forecasted != 0:
            delta_pct = round((delta / forecasted) * 100, 1)
        else:
            delta_pct = 0.0
        points.append(
            ForecastVariancePoint(
                month=key,
                forecasted_cents=forecasted,
                actual_cents=actual,
                delta_cents=delta,
                delta_pct=delta_pct,
            )
        )
        cursor = _add_months(cursor, 1)

    has_forecast = bool(forecast_by_month)
    return ForecastVarianceResponse(points=points, has_forecast=has_forecast)


# ---------------------------------------------------------------------------
# 8. Working capital — DSO / DPO / BFR
# ---------------------------------------------------------------------------


def _avg_payment_delay(
    session: Session, *, entity_id: int, direction: CommitmentDirection,
) -> tuple[float | None, int]:
    """Délai moyen entre issue_date d'un commitment et la date de la
    transaction réellement appariée. Retourne (avg_days, n).

    Calculé sur les commitments matched (status='success' ou matched_transaction_id
    not null). Si moins de 3 échantillons, retourne (None, n) pour éviter de
    publier une moyenne non significative.
    """
    rows = session.execute(
        select(
            Commitment.issue_date,
            Transaction.operation_date,
        )
        .join(Transaction, Transaction.id == Commitment.matched_transaction_id)
        .where(
            and_(
                Commitment.entity_id == entity_id,
                Commitment.direction == direction,
                Commitment.matched_transaction_id.is_not(None),
            )
        )
    ).all()
    delays = [
        (paid - issued).days
        for issued, paid in rows
        if issued is not None and paid is not None
    ]
    if len(delays) < 3:
        return None, len(delays)
    avg = sum(delays) / len(delays)
    return round(avg, 1), len(delays)


def _outstanding_amount(
    session: Session, *, entity_id: int, direction: CommitmentDirection,
) -> int:
    """Montant total des engagements en attente (status='pending') pour cette
    direction et cette entité, en centimes."""
    total = session.scalar(
        select(func.coalesce(func.sum(Commitment.amount_cents), 0))
        .where(
            and_(
                Commitment.entity_id == entity_id,
                Commitment.direction == direction,
                Commitment.status == CommitmentStatus.PENDING,
            )
        )
    )
    return int(total or 0)


def compute_working_capital(
    session: Session, *, entity_id: int,
) -> WorkingCapitalResponse:
    """Calcule DSO / DPO / BFR à partir des engagements (Commitments).

    DSO (Days Sales Outstanding) = délai moyen entre issue_date et date de
    paiement réel pour les engagements de direction IN (créances clients).
    DPO (Days Payable Outstanding) = pareil pour la direction OUT (dettes
    fournisseurs).
    BFR (Besoin en Fonds de Roulement) approximé par
        receivables_cents - payables_cents
    où receivables/payables = montants des engagements pending par direction.

    Si aucun commitment n'existe pour l'entité, has_data=False : l'UI
    affichera un état vide avec un lien vers la page Engagements.
    """
    total_commitments = session.scalar(
        select(func.count(Commitment.id))
        .where(Commitment.entity_id == entity_id)
    ) or 0
    if total_commitments == 0:
        return WorkingCapitalResponse(
            dso_days=None, dpo_days=None, bfr_cents=None,
            receivables_cents=0, payables_cents=0,
            matched_in_count=0, matched_out_count=0,
            has_data=False,
        )

    dso_days, in_count = _avg_payment_delay(
        session, entity_id=entity_id, direction=CommitmentDirection.IN
    )
    dpo_days, out_count = _avg_payment_delay(
        session, entity_id=entity_id, direction=CommitmentDirection.OUT
    )
    receivables = _outstanding_amount(
        session, entity_id=entity_id, direction=CommitmentDirection.IN
    )
    payables = _outstanding_amount(
        session, entity_id=entity_id, direction=CommitmentDirection.OUT
    )
    bfr = receivables - payables

    return WorkingCapitalResponse(
        dso_days=dso_days, dpo_days=dpo_days, bfr_cents=bfr,
        receivables_cents=receivables, payables_cents=payables,
        matched_in_count=in_count, matched_out_count=out_count,
        has_data=True,
    )
