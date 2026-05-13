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

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.category import Category
from app.models.commitment import Commitment, CommitmentDirection, CommitmentStatus
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
    insufficient_history: bool = False  # D5 : AVG_* sans données disponibles
    # True si la cellule mélange des montants au signe "inattendu" pour son
    # kind de catégorie (ex : catégorie kind='in' avec une tx négative, ou
    # kind='out' avec une tx positive). Permet à l'UI d'afficher un badge
    # d'alerte sans modifier l'agrégation.
    sign_anomaly: bool = False


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
    # Net mensuel des tx sans catégorie. Inclus dans la projection mais
    # absent de `rows` (pas une catégorie). Permet à l'UI d'afficher un
    # avertissement si > 0 — sinon l'utilisateur ne voit pas pourquoi la
    # projection diverge de la réalité.
    uncategorized_net_cents: list[int] = field(default_factory=list)


@dataclass
class Preloaded:
    """Precomputed indices for batch-efficient compute_cell.

    Toutes les valeurs monétaires sont en centimes (int), signées.
    Les clefs (cat_id, month_key) utilisent month_key = "YYYY-MM".
    """
    transactions_by_cat_month: dict[tuple[int, str], int]
    commitments_by_cat_month: dict[tuple[int, str], int]
    # Liste de toutes les ForecastLine par catégorie (plusieurs lignes
    # peuvent coexister, chacune avec sa fenêtre [start_month, end_month]).
    # `_pick_line_for_month` choisit la plus spécifique couvrant un mois.
    lines_by_cat: dict[int, list["ForecastLine"]]
    categories_by_name: dict[str, int]
    # Net mensuel des transactions sans catégorie. Indispensable pour que
    # la closing_balance_projection reflète la trésorerie réelle, sinon
    # elle diverge de la réalité en proportion des tx non-catégorisées.
    uncategorized_net_by_month: dict[str, int] = field(default_factory=dict)
    # Décomposition signe positif / signe négatif des transactions, par
    # (cat_id, month_key). Indispensable pour (1) splitter les catégories
    # kind='both' en deux lignes pivot et (2) détecter les anomalies de
    # signe (kind='in' avec montant<0, kind='out' avec montant>0).
    transactions_pos_by_cat_month: dict[tuple[int, str], int] = field(default_factory=dict)
    transactions_neg_by_cat_month: dict[tuple[int, str], int] = field(default_factory=dict)
    # Engagements PENDING split par direction (IN positif / OUT négatif).
    commitments_in_by_cat_month: dict[tuple[int, str], int] = field(default_factory=dict)
    commitments_out_by_cat_month: dict[tuple[int, str], int] = field(default_factory=dict)
    # Index Category.kind ('in' | 'out' | 'both') par id.
    kind_by_cat: dict[int, str] = field(default_factory=dict)


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


def _month_key(d: date) -> str:
    """Clé mensuelle stable au format 'YYYY-MM'."""
    return d.strftime("%Y-%m")


def _preload(
    session: Session,
    *,
    entity_id: int,
    scenario_id: int,
    from_month: date,
    to_month: date,
    account_ids: Optional[list[int]] = None,
) -> "Preloaded":
    """Charge en batch transactions/commitments/forecast_entries/lines/catégories.

    Objectif : ~4 requêtes SQL pour servir tous les ``compute_cell`` d'un pivot
    (au lieu de ~750). La plage couvre ``from_month - 12`` mois pour supporter
    les méthodes AVG_12M / SAME_MONTH_LAST_YEAR qui regardent jusqu'à 12 mois
    dans le passé.
    """
    from_first = _first_of_month(from_month)
    to_first = _first_of_month(to_month)
    earliest = _add_months(from_first, -12)
    latest = _next_month(to_first)  # exclusive upper bound

    # 1) Transactions : SUM(amount) group by (category_id, month)
    #    Décompose pos / neg pour supporter le split kind='both' et la
    #    détection des anomalies de signe (kind='in' avec tx<0, etc.).
    tx_month_col = func.date_trunc("month", Transaction.operation_date)
    tx_stmt = (
        select(
            Transaction.category_id,
            tx_month_col.label("month"),
            func.coalesce(
                func.sum(case((Transaction.amount > 0, Transaction.amount), else_=0)),
                0,
            ).label("pos"),
            func.coalesce(
                func.sum(case((Transaction.amount < 0, Transaction.amount), else_=0)),
                0,
            ).label("neg"),
        )
        .join(BankAccount, BankAccount.id == Transaction.bank_account_id)
        .where(
            and_(
                BankAccount.entity_id == entity_id,
                Transaction.operation_date >= earliest,
                Transaction.operation_date < latest,
                Transaction.is_aggregation_parent.is_(False),
                Transaction.category_id.is_not(None),
            )
        )
        .group_by(Transaction.category_id, tx_month_col)
    )
    if account_ids is not None:
        tx_stmt = tx_stmt.where(BankAccount.id.in_(account_ids))

    transactions_by_cat_month: dict[tuple[int, str], int] = {}
    transactions_pos_by_cat_month: dict[tuple[int, str], int] = {}
    transactions_neg_by_cat_month: dict[tuple[int, str], int] = {}
    for cat_id, month, pos, neg in session.execute(tx_stmt).all():
        if cat_id is None or month is None:
            continue
        key = (int(cat_id), _month_key(month))
        pos_cents = _eur_to_cents(Decimal(pos))
        neg_cents = _eur_to_cents(Decimal(neg))
        transactions_pos_by_cat_month[key] = pos_cents
        transactions_neg_by_cat_month[key] = neg_cents
        transactions_by_cat_month[key] = pos_cents + neg_cents

    # 1bis) Transactions sans catégorie : SUM(amount) group by month
    # Indispensable pour la projection de solde (sinon écart vs réalité
    # proportionnel au volume non-catégorisé).
    uncat_stmt = (
        select(
            tx_month_col.label("month"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .join(BankAccount, BankAccount.id == Transaction.bank_account_id)
        .where(
            and_(
                BankAccount.entity_id == entity_id,
                Transaction.operation_date >= earliest,
                Transaction.operation_date < latest,
                Transaction.is_aggregation_parent.is_(False),
                Transaction.category_id.is_(None),
            )
        )
        .group_by(tx_month_col)
    )
    if account_ids is not None:
        uncat_stmt = uncat_stmt.where(BankAccount.id.in_(account_ids))
    uncategorized_net_by_month: dict[str, int] = {}
    for month, total in session.execute(uncat_stmt).all():
        if month is None:
            continue
        uncategorized_net_by_month[_month_key(month)] = _eur_to_cents(
            Decimal(total)
        )

    # 2) Commitments (pending) : SUM(amount_cents) group by (cat, month, direction)
    cm_month_col = func.date_trunc("month", Commitment.expected_date)
    cm_stmt = (
        select(
            Commitment.category_id,
            cm_month_col.label("month"),
            Commitment.direction,
            func.coalesce(func.sum(Commitment.amount_cents), 0).label("total"),
        )
        .where(
            and_(
                Commitment.entity_id == entity_id,
                Commitment.status == CommitmentStatus.PENDING,
                Commitment.expected_date >= earliest,
                Commitment.expected_date < latest,
                Commitment.category_id.is_not(None),
            )
        )
        .group_by(Commitment.category_id, cm_month_col, Commitment.direction)
    )
    commitments_by_cat_month: dict[tuple[int, str], int] = {}
    commitments_in_by_cat_month: dict[tuple[int, str], int] = {}
    commitments_out_by_cat_month: dict[tuple[int, str], int] = {}
    for cat_id, month, direction, total in session.execute(cm_stmt).all():
        if cat_id is None or month is None:
            continue
        amount = int(total or 0)
        signed = amount if direction == CommitmentDirection.IN else -amount
        key = (int(cat_id), _month_key(month))
        commitments_by_cat_month[key] = commitments_by_cat_month.get(key, 0) + signed
        if direction == CommitmentDirection.IN:
            commitments_in_by_cat_month[key] = (
                commitments_in_by_cat_month.get(key, 0) + amount
            )
        else:
            commitments_out_by_cat_month[key] = (
                commitments_out_by_cat_month.get(key, 0) - amount
            )

    # 3) Lignes prévisionnelles du scénario (peuvent être multiples par cat)
    lines_by_cat: dict[int, list[ForecastLine]] = {}
    for line in session.scalars(
        select(ForecastLine).where(ForecastLine.scenario_id == scenario_id)
    ):
        lines_by_cat.setdefault(line.category_id, []).append(line)

    # 5) Index des catégories par nom (lower().strip()) — pour les formules ;
    #    et kind par id, pour le split kind='both' et la détection d'anomalies.
    categories_by_name: dict[str, int] = {}
    kind_by_cat: dict[int, str] = {}
    for cat_id, cat_name, cat_kind in session.execute(
        select(Category.id, Category.name, Category.kind)
    ).all():
        if cat_id is None:
            continue
        if cat_name is not None:
            categories_by_name[cat_name.strip().lower()] = int(cat_id)
        kind_by_cat[int(cat_id)] = cat_kind or "both"

    return Preloaded(
        transactions_by_cat_month=transactions_by_cat_month,
        commitments_by_cat_month=commitments_by_cat_month,
        lines_by_cat=lines_by_cat,
        categories_by_name=categories_by_name,
        uncategorized_net_by_month=uncategorized_net_by_month,
        transactions_pos_by_cat_month=transactions_pos_by_cat_month,
        transactions_neg_by_cat_month=transactions_neg_by_cat_month,
        commitments_in_by_cat_month=commitments_in_by_cat_month,
        commitments_out_by_cat_month=commitments_out_by_cat_month,
        kind_by_cat=kind_by_cat,
    )


def _sum_transactions(
    session: Session,
    entity_id: int,
    category_id: int,
    month: date,
    account_ids: Optional[list[int]] = None,
    *,
    preloaded: Optional["Preloaded"] = None,
) -> int:
    """Somme les transactions de la catégorie au mois donné (signées, en cents)."""
    if preloaded is not None:
        return preloaded.transactions_by_cat_month.get(
            (category_id, _month_key(_first_of_month(month))), 0
        )
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
    *,
    preloaded: Optional["Preloaded"] = None,
) -> int:
    """Somme des commitments PENDING au mois donné, signés selon direction."""
    if preloaded is not None:
        return preloaded.commitments_by_cat_month.get(
            (category_id, _month_key(_first_of_month(month))), 0
        )
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


def _avg_transactions_n_months(
    session: Session,
    entity_id: int,
    category_id: int,
    month: date,
    n_months: int,
    *,
    preloaded: Optional["Preloaded"] = None,
) -> int:
    """Moyenne des N mois précédents (excluant `month`).

    Divise par le nombre de mois ayant des données non nulles (min(n, available))
    pour éviter la sous-estimation sur historique court. Retourne 0 si aucune
    donnée n'existe sur la fenêtre.
    """
    if n_months <= 0:
        return 0
    totals = []
    for i in range(1, n_months + 1):
        m = _add_months(month, -i)
        v = _sum_transactions(session, entity_id, category_id, m, preloaded=preloaded)
        totals.append(v)

    non_zero = [v for v in totals if v != 0]
    available = len(non_zero)
    if available == 0:
        return 0

    # Division par le nombre de mois avec données, jamais par n_months fixe
    return sum(totals) // available


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
    preloaded: Optional["Preloaded"] = None,
) -> int:
    """Dispatche sur la méthode, retourne la valeur forecast en centimes (signé)."""
    method = line.method

    if method == ForecastLineMethod.RECURRING_FIXED:
        return int(line.amount_cents or 0)

    if method == ForecastLineMethod.SINGLE_MONTH_FIXED:
        # Montant ponctuel : appliqué uniquement au mois `start_month`
        # (premier jour du mois). Tous les autres mois retournent 0.
        if line.start_month is None or line.amount_cents is None:
            return 0
        line_month = date(line.start_month.year, line.start_month.month, 1)
        target_month = date(month.year, month.month, 1)
        return int(line.amount_cents) if line_month == target_month else 0

    if method == ForecastLineMethod.AVG_3M:
        return _avg_transactions_n_months(
            session, entity_id, line.category_id, month, 3, preloaded=preloaded
        )
    if method == ForecastLineMethod.AVG_6M:
        return _avg_transactions_n_months(
            session, entity_id, line.category_id, month, 6, preloaded=preloaded
        )
    if method == ForecastLineMethod.AVG_12M:
        return _avg_transactions_n_months(
            session, entity_id, line.category_id, month, 12, preloaded=preloaded
        )

    if method == ForecastLineMethod.PREVIOUS_MONTH:
        prev = _add_months(month, -1)
        return _sum_transactions(
            session, entity_id, line.category_id, prev, preloaded=preloaded
        )

    if method == ForecastLineMethod.SAME_MONTH_LAST_YEAR:
        prev = _add_months(month, -12)
        return _sum_transactions(
            session, entity_id, line.category_id, prev, preloaded=preloaded
        )

    if method == ForecastLineMethod.BASED_ON_CATEGORY:
        if line.base_category_id is None or line.ratio is None:
            return 0
        base_value = _sum_transactions(
            session, entity_id, line.base_category_id, month, preloaded=preloaded
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
            preloaded=preloaded,
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
    preloaded: Optional["Preloaded"] = None,
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
        # Résout le nom en category_id ; favoriser l'index préchargé si dispo
        cat_id: Optional[int] = None
        if preloaded is not None:
            cat_id = preloaded.categories_by_name.get(
                category_name.strip().lower()
            )
        if cat_id is None:
            cat = session.scalar(
                select(Category).where(func.lower(Category.name) == category_name)
            )
            if cat is None:
                raise FormulaError(
                    f"Catégorie '{category_name}' introuvable"
                )
            cat_id = cat.id
        target_month = _add_months(month, -month_offset)
        # Calcule la cell pour cette catégorie à ce mois, sans re-entrer dans la même formule
        cell = _compute_cell_internal(
            session,
            scenario_id=scenario_id,
            entity_id=entity_id,
            category_id=cat_id,
            month=target_month,
            seen=seen,
            preloaded=preloaded,
        )
        return Decimal(cell.total_cents)

    value = formula_evaluate(tree, resolver)
    return int(Decimal(value).to_integral_value())


# ---------------------------------------------------------------------------
# compute_cell (orchestration)
# ---------------------------------------------------------------------------


_OPEN_END_PENALTY = 10_000  # rang en mois ; toute fenêtre bornée gagne contre une fenêtre ouverte

def _line_specificity_score(line: ForecastLine) -> int:
    """Plus bas = plus spécifique.

    Hiérarchie :
      - fenêtre exactement bornée → (end - start) en mois (0 pour SINGLE_MONTH).
      - start borné, end NULL → score élevé (récurrente ouverte vers le futur).
      - start NULL et end NULL → score le plus élevé (toujours).
    """
    s = line.start_month
    e = line.end_month
    if s is not None and e is not None:
        return (e.year - s.year) * 12 + (e.month - s.month)
    if s is not None and e is None:
        return _OPEN_END_PENALTY
    if s is None and e is not None:
        return _OPEN_END_PENALTY
    return _OPEN_END_PENALTY * 2


def _line_covers_month(line: ForecastLine, month: date) -> bool:
    if line.start_month is not None and month < _first_of_month(line.start_month):
        return False
    if line.end_month is not None and month > _first_of_month(line.end_month):
        return False
    return True


def _pick_line_for_month(
    lines: list[ForecastLine], month: date
) -> Optional[ForecastLine]:
    """Sélectionne la ligne la plus spécifique couvrant `month`.

    En cas d'égalité de spécificité, on prend celle au `start_month` le plus
    récent (ordre stable : créée le plus récemment "gagne" à fenêtre égale).
    """
    candidates = [ln for ln in lines if _line_covers_month(ln, month)]
    if not candidates:
        return None
    candidates.sort(
        key=lambda ln: (
            _line_specificity_score(ln),
            -(ln.start_month.toordinal() if ln.start_month else 0),
        )
    )
    return candidates[0]


def _combine_total(
    realized: int, committed: int, forecast: int, month: date, current_month: date,
) -> int:
    if month < current_month:
        return realized
    if month > current_month:
        # Si une ForecastLine couvre ce mois (forecast != 0), respecter le choix
        # de l'utilisateur. Si aucune ligne (forecast == 0), remonter les
        # engagements PENDING pour ne pas les masquer visuellement.
        return forecast if forecast != 0 else committed
    # Mois courant
    actual = realized + committed
    if forecast == 0:
        # Pas de ligne prévisionnelle : seuls le réalisé et l'engagé comptent.
        return actual
    # Avec une ligne, le `forecast` agit comme "total attendu pour le mois" dans
    # son sens (positif → plancher d'encaissement, négatif → plancher de
    # décaissement en valeur absolue). On garde le maximum en magnitude entre
    # le réel (déjà constaté) et la prévision, dans le même signe.
    #
    # Ancien bug : `remaining = max(0, forecast - actual)` ne marchait que
    # pour les forecasts positifs. Un forecast négatif (décaissement) voyait
    # son `remaining` clampé à 0 → la cellule du mois courant tombait à
    # `actual` (souvent 0) au lieu d'afficher la prévision.
    if forecast > 0:
        return max(actual, forecast)
    return min(actual, forecast)


def _compute_cell_internal(
    session: Session,
    *,
    scenario_id: int,
    entity_id: int,
    category_id: int,
    month: date,
    account_ids: Optional[list[int]] = None,
    seen: Optional[set[tuple[int, str]]] = None,
    preloaded: Optional["Preloaded"] = None,
    sign_filter: Optional[str] = None,
) -> CellValue:
    """Calcule une cellule pivot.

    ``sign_filter`` :
      - ``None`` → comportement historique (signé, brut).
      - ``"pos"`` → ne garde que les composantes positives (montants > 0,
        commitments IN, max(forecast, 0)). Utilisé pour la ligne "entrées"
        d'une catégorie kind='both'.
      - ``"neg"`` → ne garde que les composantes négatives (montants < 0,
        commitments OUT, min(forecast, 0)). Utilisé pour la ligne "sorties"
        d'une catégorie kind='both'.
    """
    seen = seen or set()
    month = _first_of_month(month)
    current_month = _first_of_month(date.today())
    month_key = _month_key(month)

    # Décomposition pos/neg : nécessaire pour le split kind='both' et pour
    # détecter une anomalie de signe sur kind='in'/'out'.
    if preloaded is not None:
        key = (category_id, month_key)
        realized_pos = preloaded.transactions_pos_by_cat_month.get(key, 0)
        realized_neg = preloaded.transactions_neg_by_cat_month.get(key, 0)
        committed_in = preloaded.commitments_in_by_cat_month.get(key, 0)
        committed_out = preloaded.commitments_out_by_cat_month.get(key, 0)
    else:
        # Chemin sans preload (peu utilisé en prod, mais conservé pour les
        # tests unitaires de compute_cell).
        realized_signed = _sum_transactions(
            session, entity_id, category_id, month, account_ids=account_ids
        )
        committed_signed = _sum_commitments(
            session, entity_id, category_id, month
        )
        # Sans preload on n'a pas la décomposition fine : on l'approxime
        # par le signe du total agrégé, ce qui est suffisant pour les tests
        # qui n'exercent jamais le sign_filter.
        realized_pos = max(realized_signed, 0)
        realized_neg = min(realized_signed, 0)
        committed_in = max(committed_signed, 0)
        committed_out = min(committed_signed, 0)

    realized_signed = realized_pos + realized_neg
    committed_signed = committed_in + committed_out

    line: Optional[ForecastLine] = None
    forecast_signed = 0
    if month >= current_month:
        # Plusieurs lignes peuvent exister pour cette catégorie : on prend la
        # plus spécifique couvrant `month`. Ex : ponctuelle Mai bat récurrente
        # ouverte Juin→∞ pour le mois de Mai.
        if preloaded is not None:
            candidates = preloaded.lines_by_cat.get(category_id, [])
        else:
            candidates = list(
                session.scalars(
                    select(ForecastLine).where(
                        ForecastLine.scenario_id == scenario_id,
                        ForecastLine.category_id == category_id,
                    )
                )
            )
        line = _pick_line_for_month(candidates, month)
        line_value = 0
        if line is not None:
            line_value = _evaluate_line(
                session,
                line,
                scenario_id=scenario_id,
                entity_id=entity_id,
                month=month,
                seen=seen,
                preloaded=preloaded,
            )
        forecast_signed = line_value

    # Sélection de la tranche selon sign_filter
    if sign_filter == "pos":
        realized = realized_pos
        committed = committed_in
        forecast = max(forecast_signed, 0)
    elif sign_filter == "neg":
        realized = realized_neg
        committed = committed_out
        forecast = min(forecast_signed, 0)
    else:
        realized = realized_signed
        committed = committed_signed
        forecast = forecast_signed

    total = _combine_total(realized, committed, forecast, month, current_month)

    # Détection d'anomalie de signe (uniquement en mode non-filtré : les
    # rows splittés ne sont jamais "anormaux" par construction).
    sign_anomaly = False
    if sign_filter is None and preloaded is not None:
        kind = preloaded.kind_by_cat.get(category_id)
        if kind == "in" and realized_neg < 0:
            sign_anomaly = True
        elif kind == "out" and realized_pos > 0:
            sign_anomaly = True

    return CellValue(
        realized_cents=realized,
        committed_cents=committed,
        forecast_cents=forecast,
        total_cents=total,
        line_method=line.method.value if line is not None else None,
        line_params=_serialize_line_params(line) if line is not None else None,
        sign_anomaly=sign_anomaly,
    )


def compute_cell(
    session: Session,
    *,
    scenario_id: int,
    entity_id: int,
    category_id: int,
    month: date,
    account_ids: Optional[list[int]] = None,
    preloaded: Optional["Preloaded"] = None,
    sign_filter: Optional[str] = None,
) -> CellValue:
    """API publique : calcule la valeur d'une cellule pivot.

    ``preloaded`` optionnel : si fourni, les queries individuelles (tx,
    commitments, forecast entries, line) sont remplacées par des lookups
    O(1) sur les dicts préchargés.

    ``sign_filter`` (None | 'pos' | 'neg') : restreint la cellule à la
    composante positive (entrées) ou négative (sorties). Utilisé pour
    splitter les catégories kind='both'.
    """
    return _compute_cell_internal(
        session,
        scenario_id=scenario_id,
        entity_id=entity_id,
        category_id=category_id,
        month=month,
        account_ids=account_ids,
        preloaded=preloaded,
        sign_filter=sign_filter,
    )


# ---------------------------------------------------------------------------
# compute_pivot (agrégation)
# ---------------------------------------------------------------------------


def _directions_by_category(
    session: Session, entity_id: int  # entity_id conservé pour compatibilité signature
) -> dict[int, str]:
    """Retourne la direction de chaque catégorie selon Category.kind.

    kind='in'  → 'in'
    kind='out' → 'out'
    kind='both' → 'in' (convention pivot : pas de double-ligne pour les
                        catégories neutres, cohérent avec l'ancien fallback)
    """
    rows = session.execute(select(Category.id, Category.kind)).all()
    return {
        int(cat_id): ("out" if kind == "out" else "in")
        for cat_id, kind in rows
        if cat_id is not None
    }


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

    # Batch-load tout le nécessaire pour compute_cell (~4 requêtes au lieu
    # d'une cascade de queries individuelles). Cf. Plan 5c Phase 1.
    preloaded = _preload(
        session,
        entity_id=entity_id,
        scenario_id=scenario_id,
        from_month=from_month,
        to_month=to_month,
        account_ids=account_ids,
    )

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

    def _build_row(
        cat: Category,
        direction: str,
        sign_filter: Optional[str],
        label_suffix: str = "",
    ) -> Optional[PivotRow]:
        cells: list[CellValue] = []
        for m in months:
            cv = compute_cell(
                session,
                scenario_id=scenario_id,
                entity_id=entity_id,
                category_id=cat.id,
                month=m,
                account_ids=account_ids,
                preloaded=preloaded,
                sign_filter=sign_filter,
            )
            cells.append(cv)
        has_any = any(
            c.realized_cents or c.committed_cents or c.forecast_cents for c in cells
        )
        if not has_any:
            return None
        return PivotRow(
            category_id=cat.id,
            parent_id=cat.parent_category_id,
            label=f"{cat.name}{label_suffix}",
            level=level_of(cat.id),
            direction=direction,
            cells=cells,
        )

    for cat in categories:
        kind = preloaded.kind_by_cat.get(cat.id, "both")
        if kind == "both":
            # Split en deux lignes : entrées (positives) et sorties (négatives).
            row_in = _build_row(cat, "in", "pos", " (entrées)")
            row_out = _build_row(cat, "out", "neg", " (sorties)")
            if row_in is not None:
                rows.append(row_in)
            if row_out is not None:
                rows.append(row_out)
        else:
            direction = "out" if kind == "out" else "in"
            row = _build_row(cat, direction, None)
            if row is not None:
                rows.append(row)

    # Opening balance et projection
    opening = _opening_balance_cents(
        session, entity_id, from_month, account_ids=account_ids
    )
    projection: list[int] = []
    realized_series: list[dict] = []
    forecast_series: list[dict] = []
    uncategorized_series: list[int] = []
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
        # Inclure le net des transactions non-catégorisées dans la projection,
        # sinon le solde projeté diverge de la réalité bancaire (les imports
        # `opening` reflètent toutes les tx, alors que les `rows` filtrent les
        # tx catégorisées uniquement).
        uncat_net = preloaded.uncategorized_net_by_month.get(month_labels[idx], 0)
        uncategorized_series.append(uncat_net)
        running = running + month_in + month_out + uncat_net  # out déjà signé négatif
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
        uncategorized_net_cents=uncategorized_series,
        rows=rows,
        realized_series=realized_series,
        forecast_series=forecast_series,
    )
