"""Moteur de calcul prévisionnel (Plan 5b Phase 4).

Orchestration :
- `compute_cell` calcule une cellule (catégorie, mois) = realized + committed + forecast
- `_evaluate_line` dispatche sur la méthode d'une ForecastLine
- `compute_pivot` agrège toutes les catégories × tous les mois d'une plage

Conventions :
- Toutes les valeurs internes sont en **centimes (int)** pour éviter les erreurs
  d'arrondi flottant (Transaction.amount est stocké en Decimal(14,2) euros ;
  Commitment.amount_cents est un int positif avec direction séparée).
- `total` du mois courant : realized + committed + max(0, forecast - realized - committed)
- `total` mois passé : realized (pas de forecast rétroactif)
- `total` mois futur : forecast (pas de réel futur)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.category import Category
from app.models.commitment import Commitment, CommitmentDirection, CommitmentStatus
from app.models.forecast_entry import ForecastEntry
from app.models.forecast_line import ForecastLine, ForecastLineMethod
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction
from app.services.formula_parser import (
    FormulaError,
    Node,
    evaluate as formula_evaluate,
    extract_refs,
    parse as formula_parse,
)


# ---------------------------------------------------------------------------
# Dataclasses de sortie
# ---------------------------------------------------------------------------


@dataclass
class CellValue:
    realized_cents: int
    committed_cents: int
    forecast_cents: int
    total_cents: int
    line_method: Optional[str] = None
    line_params: Optional[dict] = None


@dataclass
class PivotRow:
    category_id: int
    parent_id: Optional[int]
    label: str
    level: int
    direction: str  # "in" ou "out" (inféré à partir des transactions historiques)
    cells: list[CellValue] = field(default_factory=list)


@dataclass
class PivotResult:
    months: list[str]
    opening_balance_cents: int
    closing_balance_projection_cents: list[int]
    rows: list[PivotRow]
    realized_series: list[dict]
    forecast_series: list[dict]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _first_of_month(d: date) -> date:
    return d.replace(day=1)


def _add_months(d: date, months: int) -> date:
    """Retourne le 1er du mois `d + months`, positif ou négatif."""
    d = _first_of_month(d)
    total = d.year * 12 + (d.month - 1) + months
    year, month_idx = divmod(total, 12)
    return date(year, month_idx + 1, 1)


def _next_month(d: date) -> date:
    """Retourne le 1er du mois suivant."""
    return _add_months(d, 1)


def _eur_to_cents(amount: Decimal | None) -> int:
    """Convertit un Decimal (euros) en centimes (int) sans arrondi silencieux."""
    if amount is None:
        return 0
    return int((Decimal(amount) * Decimal(100)).to_integral_value())


def _sum_transactions(
    session: Session,
    entity_id: int,
    category_id: int,
    month: date,
    account_ids: Optional[list[int]] = None,
) -> int:
    """Somme les transactions de la catégorie au mois donné (signées, en cents)."""
    start = _first_of_month(month)
    end = _next_month(start)
    stmt = select(func.coalesce(func.sum(Transaction.amount), 0)).join(
        BankAccount, BankAccount.id == Transaction.bank_account_id
    ).where(
        and_(
            BankAccount.entity_id == entity_id,
            Transaction.category_id == category_id,
            Transaction.operation_date >= start,
            Transaction.operation_date < end,
            Transaction.is_aggregation_parent.is_(False),
        )
    )
    if account_ids is not None:
        stmt = stmt.where(BankAccount.id.in_(account_ids))
    total = session.execute(stmt).scalar_one()
    return _eur_to_cents(Decimal(total))


def _sum_commitments(
    session: Session,
    entity_id: int,
    category_id: int,
    month: date,
) -> int:
    """Somme des commitments PENDING au mois donné, signés selon direction."""
    start = _first_of_month(month)
    end = _next_month(start)
    rows = session.execute(
        select(Commitment.direction, func.coalesce(func.sum(Commitment.amount_cents), 0))
        .where(
            and_(
                Commitment.entity_id == entity_id,
                Commitment.category_id == category_id,
                Commitment.status == CommitmentStatus.PENDING,
                Commitment.expected_date >= start,
                Commitment.expected_date < end,
            )
        )
        .group_by(Commitment.direction)
    ).all()
    total = 0
    for direction, amount in rows:
        signed = int(amount) if direction == CommitmentDirection.IN else -int(amount)
        total += signed
    return total


def _sum_forecast_entries(
    session: Session,
    entity_id: int,
    category_id: int,
    month: date,
) -> int:
    """Somme des ForecastEntry manuelles au mois donné (amount en Decimal euros)."""
    start = _first_of_month(month)
    end = _next_month(start)
    total = session.execute(
        select(func.coalesce(func.sum(ForecastEntry.amount), 0)).where(
            and_(
                ForecastEntry.entity_id == entity_id,
                ForecastEntry.category_id == category_id,
                ForecastEntry.due_date >= start,
                ForecastEntry.due_date < end,
            )
        )
    ).scalar_one()
    return _eur_to_cents(Decimal(total))


def _avg_transactions_n_months(
    session: Session,
    entity_id: int,
    category_id: int,
    month: date,
    n_months: int,
) -> int:
    """Moyenne des N mois précédents (excluant le mois `month` lui-même)."""
    if n_months <= 0:
        return 0
    # Prend les N mois strictement avant `month`
    total = 0
    for i in range(1, n_months + 1):
        m = _add_months(month, -i)
        total += _sum_transactions(session, entity_id, category_id, m)
    # Division entière (centimes)
    return total // n_months


# ---------------------------------------------------------------------------
# Évaluation d'une ligne selon sa méthode
# ---------------------------------------------------------------------------


def _serialize_line_params(line: ForecastLine) -> dict:
    return {
        "amount_cents": line.amount_cents,
        "base_category_id": line.base_category_id,
        "ratio": str(line.ratio) if line.ratio is not None else None,
        "formula_expr": line.formula_expr,
    }


def _evaluate_line(
    session: Session,
    line: ForecastLine,
    *,
    scenario_id: int,
    entity_id: int,
    month: date,
    seen: Optional[set[tuple[int, str]]] = None,
) -> int:
    """Dispatche sur la méthode, retourne la valeur forecast en centimes (signé)."""
    method = line.method

    if method == ForecastLineMethod.RECURRING_FIXED:
        return int(line.amount_cents or 0)

    if method == ForecastLineMethod.AVG_3M:
        return _avg_transactions_n_months(session, entity_id, line.category_id, month, 3)
    if method == ForecastLineMethod.AVG_6M:
        return _avg_transactions_n_months(session, entity_id, line.category_id, month, 6)
    if method == ForecastLineMethod.AVG_12M:
        return _avg_transactions_n_months(session, entity_id, line.category_id, month, 12)

    if method == ForecastLineMethod.PREVIOUS_MONTH:
        prev = _add_months(month, -1)
        return _sum_transactions(session, entity_id, line.category_id, prev)

    if method == ForecastLineMethod.SAME_MONTH_LAST_YEAR:
        prev = _add_months(month, -12)
        return _sum_transactions(session, entity_id, line.category_id, prev)

    if method == ForecastLineMethod.BASED_ON_CATEGORY:
        if line.base_category_id is None or line.ratio is None:
            return 0
        base_value = _sum_transactions(
            session, entity_id, line.base_category_id, month
        )
        # ratio est un Decimal ; arrondit au centime près
        return int(
            (Decimal(base_value) * Decimal(line.ratio)).to_integral_value()
        )

    if method == ForecastLineMethod.FORMULA:
        if not line.formula_expr:
            return 0
        return _evaluate_formula(
            session,
            scenario_id=scenario_id,
            entity_id=entity_id,
            target_category_id=line.category_id,
            formula_expr=line.formula_expr,
            month=month,
            seen=seen or set(),
        )

    return 0


def _evaluate_formula(
    session: Session,
    *,
    scenario_id: int,
    entity_id: int,
    target_category_id: int,
    formula_expr: str,
    month: date,
    seen: set[tuple[int, str]],
) -> int:
    """Parse + évalue une formule avec resolver récursif protégé contre les cycles."""
    key = (target_category_id, month.isoformat())
    if key in seen:
        raise FormulaError(
            f"Cycle détecté dans la formule de la catégorie {target_category_id}"
        )
    seen = seen | {key}

    try:
        tree: Node = formula_parse(formula_expr)
    except FormulaError:
        raise

    def resolver(category_name: str, month_offset: int) -> Decimal:
        # Résout le nom en category_id
        cat = session.scalar(
            select(Category).where(func.lower(Category.name) == category_name)
        )
        if cat is None:
            raise FormulaError(
                f"Catégorie '{category_name}' introuvable"
            )
        target_month = _add_months(month, -month_offset)
        # Calcule la cell pour cette catégorie à ce mois, sans re-entrer dans la même formule
        cell = _compute_cell_internal(
            session,
            scenario_id=scenario_id,
            entity_id=entity_id,
            category_id=cat.id,
            month=target_month,
            seen=seen,
        )
        return Decimal(cell.total_cents)

    value = formula_evaluate(tree, resolver)
    return int(Decimal(value).to_integral_value())


# ---------------------------------------------------------------------------
# compute_cell (orchestration)
# ---------------------------------------------------------------------------


def _combine_total(
    realized: int, committed: int, forecast: int, month: date, current_month: date,
) -> int:
    if month < current_month:
        return realized
    if month > current_month:
        return forecast
    # mois courant
    remaining = forecast - realized - committed
    if remaining < 0:
        remaining = 0
    return realized + committed + remaining


def _compute_cell_internal(
    session: Session,
    *,
    scenario_id: int,
    entity_id: int,
    category_id: int,
    month: date,
    account_ids: Optional[list[int]] = None,
    seen: Optional[set[tuple[int, str]]] = None,
) -> CellValue:
    seen = seen or set()
    month = _first_of_month(month)
    current_month = _first_of_month(date.today())

    realized = _sum_transactions(
        session, entity_id, category_id, month, account_ids=account_ids
    )
    committed = _sum_commitments(session, entity_id, category_id, month)

    line: Optional[ForecastLine] = None
    forecast = 0
    if month >= current_month:
        line = session.scalar(
            select(ForecastLine).where(
                ForecastLine.scenario_id == scenario_id,
                ForecastLine.category_id == category_id,
            )
        )
        line_value = 0
        if line is not None:
            # Respect start_month / end_month si définis
            if (line.start_month is None or month >= _first_of_month(line.start_month)) and (
                line.end_month is None or month <= _first_of_month(line.end_month)
            ):
                line_value = _evaluate_line(
                    session,
                    line,
                    scenario_id=scenario_id,
                    entity_id=entity_id,
                    month=month,
                    seen=seen,
                )
        manual = _sum_forecast_entries(session, entity_id, category_id, month)
        forecast = line_value + manual

    total = _combine_total(realized, committed, forecast, month, current_month)

    return CellValue(
        realized_cents=realized,
        committed_cents=committed,
        forecast_cents=forecast,
        total_cents=total,
        line_method=line.method.value if line is not None else None,
        line_params=_serialize_line_params(line) if line is not None else None,
    )


def compute_cell(
    session: Session,
    *,
    scenario_id: int,
    entity_id: int,
    category_id: int,
    month: date,
    account_ids: Optional[list[int]] = None,
) -> CellValue:
    """API publique : calcule la valeur d'une cellule pivot."""
    return _compute_cell_internal(
        session,
        scenario_id=scenario_id,
        entity_id=entity_id,
        category_id=category_id,
        month=month,
        account_ids=account_ids,
    )


# ---------------------------------------------------------------------------
# compute_pivot (agrégation)
# ---------------------------------------------------------------------------


def _infer_direction(session: Session, entity_id: int, category_id: int) -> str:
    """Infère "in" ou "out" en regardant la somme historique des transactions.

    Si la somme est >= 0 → "in", sinon "out". En cas d'absence d'historique,
    défaut à "in". Ce choix est pragmatique car Horizon n'a pas de champ
    Category.kind (cf. Concerns dans le rapport).
    """
    total = session.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .join(BankAccount, BankAccount.id == Transaction.bank_account_id)
        .where(
            and_(
                BankAccount.entity_id == entity_id,
                Transaction.category_id == category_id,
            )
        )
    ).scalar_one()
    return "in" if Decimal(total) >= 0 else "out"


def _months_range(from_month: date, to_month: date) -> list[date]:
    months: list[date] = []
    cur = _first_of_month(from_month)
    end = _first_of_month(to_month)
    while cur <= end:
        months.append(cur)
        cur = _next_month(cur)
    return months


def _opening_balance_cents(
    session: Session,
    entity_id: int,
    from_month: date,
    account_ids: Optional[list[int]] = None,
) -> int:
    """Σ des derniers closing_balance par compte strictement avant from_month."""
    start = _first_of_month(from_month)
    # Résout les comptes
    ba_stmt = select(BankAccount.id).where(BankAccount.entity_id == entity_id)
    if account_ids is not None:
        ba_stmt = ba_stmt.where(BankAccount.id.in_(account_ids))
    ba_ids = list(session.scalars(ba_stmt))
    if not ba_ids:
        return 0

    latest_per_account = (
        select(
            ImportRecord.bank_account_id.label("ba_id"),
            func.max(ImportRecord.period_end).label("last_end"),
        )
        .where(
            and_(
                ImportRecord.bank_account_id.in_(ba_ids),
                ImportRecord.status == ImportStatus.COMPLETED,
                ImportRecord.closing_balance.is_not(None),
                ImportRecord.period_end.is_not(None),
                ImportRecord.period_end < start,
            )
        )
        .group_by(ImportRecord.bank_account_id)
        .subquery()
    )
    rows = session.execute(
        select(ImportRecord.closing_balance).join(
            latest_per_account,
            and_(
                ImportRecord.bank_account_id == latest_per_account.c.ba_id,
                ImportRecord.period_end == latest_per_account.c.last_end,
            ),
        )
    ).all()
    total = sum((Decimal(r.closing_balance) for r in rows), Decimal("0"))
    return _eur_to_cents(total)


def compute_pivot(
    session: Session,
    *,
    scenario_id: int,
    entity_id: int,
    from_month: date,
    to_month: date,
    account_ids: Optional[list[int]] = None,
) -> PivotResult:
    """Agrège cellule (catégorie, mois) en un pivot complet."""
    months = _months_range(from_month, to_month)
    month_labels = [m.strftime("%Y-%m") for m in months]

    # Récupère toutes les catégories (arbre plat) — filtre : celles ayant au
    # moins une transaction/commitment/line dans ce scope, pour limiter le bruit.
    # Simplification v1 : toutes les catégories.
    categories = list(
        session.scalars(select(Category).order_by(Category.name))
    )

    # Calcule le level dans l'arbre (0 = root, 1 = enfant direct, …)
    cat_by_id = {c.id: c for c in categories}

    def level_of(cid: int) -> int:
        depth = 0
        cur = cat_by_id.get(cid)
        while cur is not None and cur.parent_category_id is not None:
            depth += 1
            cur = cat_by_id.get(cur.parent_category_id)
            if depth > 10:  # garde-fou anti-cycle
                break
        return depth

    rows: list[PivotRow] = []
    for cat in categories:
        cells: list[CellValue] = []
        for m in months:
            cv = compute_cell(
                session,
                scenario_id=scenario_id,
                entity_id=entity_id,
                category_id=cat.id,
                month=m,
                account_ids=account_ids,
            )
            cells.append(cv)
        # Ne conserver que les catégories qui ont au moins une valeur non nulle
        has_any = any(
            c.realized_cents or c.committed_cents or c.forecast_cents for c in cells
        )
        if not has_any:
            continue
        direction = _infer_direction(session, entity_id, cat.id)
        rows.append(
            PivotRow(
                category_id=cat.id,
                parent_id=cat.parent_category_id,
                label=cat.name,
                level=level_of(cat.id),
                direction=direction,
                cells=cells,
            )
        )

    # Opening balance et projection
    opening = _opening_balance_cents(
        session, entity_id, from_month, account_ids=account_ids
    )
    projection: list[int] = []
    realized_series: list[dict] = []
    forecast_series: list[dict] = []
    running = opening
    for idx, m in enumerate(months):
        month_in = 0
        month_out = 0
        month_realized_in = 0
        month_realized_out = 0
        month_forecast_in = 0
        month_forecast_out = 0
        for row in rows:
            cell = row.cells[idx]
            if row.direction == "in":
                month_in += cell.total_cents
                month_realized_in += cell.realized_cents
                month_forecast_in += cell.forecast_cents
            else:
                month_out += cell.total_cents
                month_realized_out += cell.realized_cents
                month_forecast_out += cell.forecast_cents
        running = running + month_in + month_out  # out déjà signé négatif
        projection.append(running)
        realized_series.append(
            {
                "month": month_labels[idx],
                "in": month_realized_in,
                "out": month_realized_out,
            }
        )
        forecast_series.append(
            {
                "month": month_labels[idx],
                "in": month_forecast_in,
                "out": month_forecast_out,
            }
        )

    return PivotResult(
        months=month_labels,
        opening_balance_cents=opening,
        closing_balance_projection_cents=projection,
        rows=rows,
        realized_series=realized_series,
        forecast_series=forecast_series,
    )
