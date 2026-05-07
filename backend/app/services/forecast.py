"""Calcul de la projection de trésorerie + détection de récurrences."""
from __future__ import annotations

import calendar
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from statistics import median

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.counterparty import Counterparty, CounterpartyStatus
from app.models.transaction import Transaction
from app.schemas.forecast import (
    DetectedRecurrenceSuggestion,
    ForecastProjection,
    ForecastProjectionPoint,
    ForecastRecurrence,
)


def _add_months(d: date, months: int) -> date:
    """Ajoute `months` à `d` en clampant le jour si le mois cible est plus court."""
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(d.day, last_day))


def compute_projection(
    db: Session,
    *,
    bank_account_ids: list[int],
    accessible_entity_ids: list[int],
    entity_id: int | None,
    starting_balance: Decimal,
    starting_date: date,
    horizon_days: int,
) -> ForecastProjection:
    """Projette le solde à partir de `starting_balance` sur `horizon_days`.

    Depuis D1, forecast_entries n'existe plus. La projection retourne une
    courbe plate depuis starting_balance — elle sert uniquement à afficher le
    solde courant en point de départ de la ligne de projection sur 90 jours.
    Les ForecastLine (pivot) sont la source de vérité pour le prévisionnel.
    """
    horizon_end = starting_date + timedelta(days=horizon_days)

    points: list[ForecastProjectionPoint] = []
    running = starting_balance
    cur = starting_date
    while cur <= horizon_end:
        points.append(
            ForecastProjectionPoint(date=cur, balance=running, planned_net=Decimal("0"))
        )
        cur = cur + timedelta(days=1)

    return ForecastProjection(
        starting_balance=starting_balance,
        starting_date=starting_date,
        horizon_days=horizon_days,
        points=points,
    )


@dataclass(frozen=True)
class _Occurrence:
    operation_date: date
    amount: Decimal


def detect_recurring(
    db: Session,
    *,
    entity_id: int,
    bank_account_ids: list[int],
    lookback_days: int = 180,
    min_occurrences: int = 3,
) -> list[DetectedRecurrenceSuggestion]:
    """Détection naïve de récurrences par contrepartie.

    Algorithme :
    1. Pour chaque contrepartie ACTIVE ou PENDING avec >= `min_occurrences`
       transactions dans les `lookback_days` derniers jours.
    2. On calcule la médiane du delta en jours entre transactions successives.
       Si cette médiane est dans [25, 35] → MONTHLY.
       Si dans [6, 8] → WEEKLY. Sinon, ignoré.
    3. Le montant suggéré est la médiane des montants (conservant le signe).
    4. La prochaine date attendue = last_occurrence + median_step.
    """
    today = date.today()
    since = today - timedelta(days=lookback_days)

    rows = db.execute(
        select(
            Transaction.counterparty_id,
            Counterparty.name,
            Transaction.operation_date,
            Transaction.amount,
        )
        .select_from(Transaction)
        .join(Counterparty, Counterparty.id == Transaction.counterparty_id)
        .where(
            and_(
                Transaction.bank_account_id.in_(bank_account_ids),
                Transaction.operation_date >= since,
                Transaction.is_aggregation_parent.is_(False),
                Counterparty.entity_id == entity_id,
                Counterparty.status != CounterpartyStatus.IGNORED,
            )
        )
        .order_by(Transaction.counterparty_id, Transaction.operation_date)
    ).all()

    by_cp: dict[tuple[int, str], list[_Occurrence]] = defaultdict(list)
    for r in rows:
        if r.counterparty_id is None:
            continue
        by_cp[(r.counterparty_id, r.name)].append(
            _Occurrence(operation_date=r.operation_date, amount=Decimal(r.amount))
        )

    suggestions: list[DetectedRecurrenceSuggestion] = []
    for (cp_id, cp_name), occs in by_cp.items():
        if len(occs) < min_occurrences:
            continue
        occs = sorted(occs, key=lambda o: o.operation_date)
        deltas = [
            (occs[i].operation_date - occs[i - 1].operation_date).days
            for i in range(1, len(occs))
        ]
        med_delta = median(deltas)
        if 25 <= med_delta <= 35:
            recurrence = ForecastRecurrence.MONTHLY
            step_days = 30
        elif 6 <= med_delta <= 8:
            recurrence = ForecastRecurrence.WEEKLY
            step_days = 7
        elif 85 <= med_delta <= 100:
            recurrence = ForecastRecurrence.QUARTERLY
            step_days = 91
        else:
            continue

        amounts = sorted(o.amount for o in occs)
        mid = len(amounts) // 2
        avg_amount = (
            amounts[mid]
            if len(amounts) % 2 == 1
            else (amounts[mid - 1] + amounts[mid]) / 2
        )
        last = occs[-1].operation_date
        next_expected = last + timedelta(days=step_days)

        suggestions.append(
            DetectedRecurrenceSuggestion(
                counterparty_id=cp_id,
                counterparty_name=cp_name,
                average_amount=avg_amount,
                last_occurrence=last,
                next_expected=next_expected,
                recurrence=recurrence,
                occurrences_count=len(occs),
                entity_id=entity_id,
            )
        )

    suggestions.sort(key=lambda s: abs(s.average_amount), reverse=True)
    return suggestions
