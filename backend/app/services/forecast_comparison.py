"""Snapshot mensuel du prévisionnel + service de comparaison prévu/réalisé.

Deux responsabilités :

1. ``snapshot_month`` : pour un (scenario, month) donné, fige les valeurs
   prédites de toutes les catégories qui ont une règle prévisionnelle
   couvrant ce mois. Le snapshot est stable même si les ForecastLine ou
   l'historique des transactions changent ensuite.

2. ``compute_comparison`` : pour une plage de mois passés, retourne par
   catégorie ``{forecast (snapshot), realized (transactions), écart}`` et
   les totaux agrégés in/out + variation nette. Sert la vue « Suivi des
   écarts » côté UI.

L'auto-snapshot est branché dans ``compute_pivot`` : tout mois passé d'une
plage visualisée et sans snapshot est figé à la volée. Une fonction
explicite ``snapshot_month`` est aussi exposée pour le re-snapshot
manuel via l'API ("Re-clôturer le mois M").
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.category import Category
from app.models.forecast_line import ForecastLine
from app.models.forecast_month_snapshot import ForecastMonthSnapshot
from app.models.forecast_scenario import ForecastScenario
from app.models.transaction import Transaction
from app.services.forecast_engine import (
    _add_months,
    _evaluate_line,
    _first_of_month,
    _pick_line_for_month,
    _preload,
)


# ---------------------------------------------------------------------------
# Dataclasses de sortie
# ---------------------------------------------------------------------------


@dataclass
class ComparisonRow:
    category_id: int
    label: str
    direction: str  # "in" | "out"
    forecast_cents: int  # 0 si pas de snapshot pour cette catégorie
    realized_cents: int
    ecart_cents: int  # realized - forecast (signed)
    ecart_pct: Optional[float]  # None si forecast == 0
    status: str  # "green" | "amber" | "red" | "no-forecast"


@dataclass
class ComparisonMonth:
    month: str  # "YYYY-MM"
    is_snapshotted: bool  # True dès qu'au moins un snapshot existe pour ce mois
    rows: list[ComparisonRow]
    total_in_forecast_cents: int
    total_in_realized_cents: int
    total_out_forecast_cents: int
    total_out_realized_cents: int
    net_forecast_cents: int
    net_realized_cents: int


@dataclass
class ComparisonResult:
    months: list[ComparisonMonth] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


def snapshot_month(
    session: Session,
    *,
    scenario_id: int,
    month: date,
    is_auto: bool = True,
) -> int:
    """Fige les valeurs prédites de toutes les catégories pour ``month``.

    Retourne le nombre de cellules snapshottées. UPSERT : un snapshot
    existant pour la même clé (scenario, category, month) est remplacé
    (la valeur prédite peut changer si l'utilisateur a édité ses lignes
    prévisionnelles entre deux clôtures).
    """
    month = _first_of_month(month)

    sc = session.get(ForecastScenario, scenario_id)
    if sc is None:
        return 0

    preloaded = _preload(
        session,
        entity_id=sc.entity_id,
        scenario_id=scenario_id,
        from_month=month,
        to_month=month,
    )

    snapshotted = 0
    for category_id, lines in preloaded.lines_by_cat.items():
        line = _pick_line_for_month(lines, month)
        if line is None:
            continue
        # On évalue la ligne comme si le mois était dans le futur : c'est
        # exactement la valeur que l'utilisateur voyait avant que le mois
        # ne bascule en passé.
        value = _evaluate_line(
            session,
            line,
            scenario_id=scenario_id,
            entity_id=sc.entity_id,
            month=month,
            preloaded=preloaded,
        )
        if value == 0:
            continue

        stmt = pg_insert(ForecastMonthSnapshot).values(
            scenario_id=scenario_id,
            category_id=category_id,
            month=month,
            forecast_cents=int(value),
            is_auto=is_auto,
        ).on_conflict_do_update(
            index_elements=["scenario_id", "category_id", "month"],
            set_={
                "forecast_cents": int(value),
                "is_auto": is_auto,
                "updated_at": func.now(),
            },
        )
        session.execute(stmt)
        snapshotted += 1

    session.commit()
    return snapshotted


def auto_snapshot_past_months(
    session: Session,
    *,
    scenario_id: int,
    from_month: date,
    to_month: date,
) -> int:
    """Pour chaque mois passé dans [from_month, to_month] qui n'a aucun
    snapshot pour ce scénario, en fige un automatiquement.

    Appelé en fin de ``compute_pivot`` (lazy auto-snapshot). Limite : ne
    snapshotte que les mois STRICTEMENT passés (mois courant exclu).
    """
    current = _first_of_month(date.today())
    cur = _first_of_month(from_month)
    end = _first_of_month(to_month)

    snapshotted_total = 0
    while cur <= end:
        if cur < current:
            # Existe-t-il déjà au moins un snapshot pour ce (scenario, month) ?
            exists = session.scalar(
                select(func.count(ForecastMonthSnapshot.id)).where(
                    ForecastMonthSnapshot.scenario_id == scenario_id,
                    ForecastMonthSnapshot.month == cur,
                )
            )
            if not exists:
                snapshotted_total += snapshot_month(
                    session, scenario_id=scenario_id, month=cur, is_auto=True
                )
        cur = _add_months(cur, 1)
    return snapshotted_total


# ---------------------------------------------------------------------------
# Comparaison
# ---------------------------------------------------------------------------


def _ecart_status(
    forecast_cents: int, realized_cents: int
) -> tuple[Optional[float], str]:
    """Retourne (écart en %, status). Convention :
      - vert si |écart| < 10 %
      - ambre si |écart| < 25 %
      - rouge sinon
      - no-forecast si forecast == 0
    """
    if forecast_cents == 0:
        return (None, "no-forecast")
    ecart_pct = abs(realized_cents - forecast_cents) / abs(forecast_cents) * 100.0
    if ecart_pct < 10:
        status = "green"
    elif ecart_pct < 25:
        status = "amber"
    else:
        status = "red"
    return (ecart_pct, status)


def _months_range(from_month: date, to_month: date) -> list[date]:
    out: list[date] = []
    cur = _first_of_month(from_month)
    end = _first_of_month(to_month)
    while cur <= end:
        out.append(cur)
        cur = _add_months(cur, 1)
    return out


def compute_comparison(
    session: Session,
    *,
    scenario_id: int,
    entity_id: int,
    from_month: date,
    to_month: date,
) -> ComparisonResult:
    """Construit la comparaison prévu vs réalisé pour la plage demandée.

    Ne renvoie que les mois ayant au moins un snapshot. Les mois sans
    snapshot (jamais ouverts post-clôture ou rangées dans le futur) sont
    listés avec ``is_snapshotted=False`` et des totaux à 0.
    """
    months = _months_range(from_month, to_month)
    if not months:
        return ComparisonResult(months=[])

    # Auto-snapshot lazy : avant de calculer la comparaison, on fige les
    # mois passés qui n'ont pas encore de snapshot. Garantit une vue
    # cohérente même si l'utilisateur arrive sur la page sans avoir
    # cliqué "Re-clôturer".
    auto_snapshot_past_months(
        session,
        scenario_id=scenario_id,
        from_month=from_month,
        to_month=to_month,
    )

    # 1) Snapshots de la plage
    snapshots = session.execute(
        select(
            ForecastMonthSnapshot.category_id,
            ForecastMonthSnapshot.month,
            ForecastMonthSnapshot.forecast_cents,
        ).where(
            ForecastMonthSnapshot.scenario_id == scenario_id,
            ForecastMonthSnapshot.month >= months[0],
            ForecastMonthSnapshot.month <= months[-1],
        )
    ).all()
    snap_by_month: dict[date, dict[int, int]] = {}
    for cat_id, m, cents in snapshots:
        snap_by_month.setdefault(m, {})[int(cat_id)] = int(cents)

    # 2) Transactions réelles par (cat, month) sur la plage
    tx_month_col = func.date_trunc("month", Transaction.operation_date)
    tx_stmt = (
        select(
            Transaction.category_id,
            tx_month_col.label("month"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .join(BankAccount, BankAccount.id == Transaction.bank_account_id)
        .where(
            and_(
                BankAccount.entity_id == entity_id,
                Transaction.operation_date >= months[0],
                Transaction.operation_date < _add_months(months[-1], 1),
                Transaction.is_aggregation_parent.is_(False),
                Transaction.category_id.is_not(None),
            )
        )
        .group_by(Transaction.category_id, tx_month_col)
    )
    realized_by_month: dict[date, dict[int, int]] = {}
    for cat_id, m, total in session.execute(tx_stmt).all():
        if cat_id is None or m is None:
            continue
        cents = int((Decimal(total) * Decimal(100)).to_integral_value())
        # `m` retourné par date_trunc est un datetime → on normalise.
        key = date(m.year, m.month, 1)
        realized_by_month.setdefault(key, {})[int(cat_id)] = cents

    # 3) Métadonnées catégories
    cats = {
        c.id: c
        for c in session.scalars(select(Category)).all()
    }

    def direction_of(cat: Category, *, forecast: int, realized: int) -> str:
        if cat.kind == "in":
            return "in"
        if cat.kind == "out":
            return "out"
        # 'both' : on classe par signe du signal le plus parlant (forecast
        # prioritaire, sinon realized). Évite que des entrées de TVA
        # remontent côté "out" et réciproquement.
        ref = forecast if forecast != 0 else realized
        return "out" if ref < 0 else "in"

    # 4) Construction des mois
    result_months: list[ComparisonMonth] = []
    for m in months:
        snap = snap_by_month.get(m, {})
        realized = realized_by_month.get(m, {})
        all_cat_ids = set(snap.keys()) | set(realized.keys())

        rows: list[ComparisonRow] = []
        total_in_f = total_in_r = total_out_f = total_out_r = 0
        for cat_id in sorted(
            all_cat_ids, key=lambda c: cats[c].name if c in cats else ""
        ):
            cat = cats.get(cat_id)
            if cat is None:
                continue
            f_cents = snap.get(cat_id, 0)
            r_cents = realized.get(cat_id, 0)
            ecart = r_cents - f_cents
            ecart_pct, status = _ecart_status(f_cents, r_cents)
            direction = direction_of(cat, forecast=f_cents, realized=r_cents)
            rows.append(
                ComparisonRow(
                    category_id=cat_id,
                    label=cat.name,
                    direction=direction,
                    forecast_cents=f_cents,
                    realized_cents=r_cents,
                    ecart_cents=ecart,
                    ecart_pct=ecart_pct,
                    status=status,
                )
            )
            if direction == "in":
                total_in_f += f_cents
                total_in_r += r_cents
            else:
                total_out_f += f_cents
                total_out_r += r_cents

        result_months.append(
            ComparisonMonth(
                month=m.strftime("%Y-%m"),
                is_snapshotted=bool(snap),
                rows=rows,
                total_in_forecast_cents=total_in_f,
                total_in_realized_cents=total_in_r,
                total_out_forecast_cents=total_out_f,
                total_out_realized_cents=total_out_r,
                net_forecast_cents=total_in_f + total_out_f,
                net_realized_cents=total_in_r + total_out_r,
            )
        )

    return ComparisonResult(months=result_months)
