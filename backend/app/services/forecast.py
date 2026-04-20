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
from app.models.forecast_entry import ForecastEntry, ForecastRecurrence
from app.models.transaction import Transaction
from app.schemas.forecast import (
    DetectedRecurrenceSuggestion,
    ForecastProjection,
    ForecastProjectionPoint,
)


def _add_months(d: date, months: int) -> date:
    """Ajoute `months` à `d` en clampant le jour si le mois cible est plus court."""
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(d.day, last_day))


def _expand_entry(
    entry: ForecastEntry, *, start: date, end: date,
) -> list[tuple[date, Decimal]]:
    """Retourne la liste des occurrences (date, montant) dans [start, end]."""
    if entry.due_date > end:
        return []

    amount = Decimal(entry.amount)
    if entry.recurrence == ForecastRecurrence.NONE:
        if entry.due_date < start:
            return []
        return [(entry.due_date, amount)]

    step_days: int | None = {
        ForecastRecurrence.WEEKLY: 7,
    }.get(entry.recurrence)

    months_step: int | None = {
        ForecastRecurrence.MONTHLY: 1,
        ForecastRecurrence.QUARTERLY: 3,
        ForecastRecurrence.YEARLY: 12,
    }.get(entry.recurrence)

    out: list[tuple[date, Decimal]] = []
    limit = entry.recurrence_until if entry.recurrence_until else end
    cur = entry.due_date
    # Avance jusqu'à la première occurrence >= start
    if step_days is not None:
        if cur < start:
            steps = (start - cur).days // step_days
            cur = cur + timedelta(days=steps * step_days)
            if cur < start:
                cur = cur + timedelta(days=step_days)
        while cur <= end and cur <= limit:
            out.append((cur, amount))
            cur = cur + timedelta(days=step_days)
    elif months_step is not None:
        while cur < start and cur <= limit:
            cur = _add_months(cur, months_step)
        while cur <= end and cur <= limit:
            out.append((cur, amount))
            cur = _add_months(cur, months_step)
    return out


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

    Les occurrences agrégées proviennent des `ForecastEntry` de l'entité
    courante (ou toutes accessibles). Les transactions déjà passées ne sont
    pas ajoutées — on postule que `starting_balance` les intègre déjà.
    """
    horizon_end = starting_date + timedelta(days=horizon_days)

    entity_filter = (
        [ForecastEntry.entity_id == entity_id]
        if entity_id is not None
        else [ForecastEntry.entity_id.in_(accessible_entity_ids)]
    )
    entries = db.execute(
        select(ForecastEntry).where(and_(*entity_filter))
    ).scalars().all()

    # Si bank_account_id renseigné sur l'entry et qu'on filtre par entity,
    # on conserve l'entry si elle appartient à un compte de l'entité.
    # (Déjà garanti via entity_filter.)

    daily_net: dict[date, Decimal] = defaultdict(lambda: Decimal("0"))
    for entry in entries:
        for d, amt in _expand_entry(
            entry, start=starting_date + timedelta(days=1), end=horizon_end,
        ):
            daily_net[d] += amt

    # Marque consciemment : on n'ajoute PAS les transactions futures (il n'y
    # en a pas, par définition). Pas non plus les récurrences détectées
    # automatiquement — elles sont exposées en suggestions côté UI, l'utilisateur
    # choisit de les matérialiser en ForecastEntry.

    points: list[ForecastProjectionPoint] = []
    running = starting_balance
    cur = starting_date
    while cur <= horizon_end:
        net = daily_net.get(cur, Decimal("0"))
        running = running + net
        points.append(
            ForecastProjectionPoint(date=cur, balance=running, planned_net=net)
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
