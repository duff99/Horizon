"""Schemas Pydantic pour les endpoints `/api/analysis/*`.

Tous les montants sont exprimés en centimes (int) sauf mention contraire.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 1. Category drift
# ---------------------------------------------------------------------------


class CategoryDriftRow(BaseModel):
    category_id: int
    label: str
    current_cents: int
    avg3m_cents: int
    delta_cents: int
    delta_pct: float
    status: Literal["alert", "normal"]


class CategoryDriftResponse(BaseModel):
    rows: list[CategoryDriftRow]
    seuil_pct: float


class CategoryDriftTransaction(BaseModel):
    """Une transaction qui contribue à la dérive du mois courant."""

    id: int
    operation_date: str  # ISO YYYY-MM-DD
    label: str
    counterparty: str | None
    amount_cents: int


class CategoryDriftDetailResponse(BaseModel):
    """Détail des transactions du mois courant pour une catégorie donnée."""

    category_id: int
    category_label: str
    month: str  # ISO YYYY-MM
    total_cents: int
    transactions: list[CategoryDriftTransaction]


# ---------------------------------------------------------------------------
# 7. Forecast variance (réalisé vs prévu)
# ---------------------------------------------------------------------------


class ForecastVariancePoint(BaseModel):
    """Variance d'un mois : prévu vs réalisé, en centimes."""

    month: str  # YYYY-MM
    forecasted_cents: int
    actual_cents: int
    delta_cents: int  # actual - forecast (signé)
    delta_pct: float  # 0.0 si forecast = 0


class ForecastVarianceResponse(BaseModel):
    points: list[ForecastVariancePoint]
    has_forecast: bool  # False si aucune entrée prévisionnelle saisie


# ---------------------------------------------------------------------------
# 8. Working capital (DSO / DPO / BFR)
# ---------------------------------------------------------------------------


class WorkingCapitalResponse(BaseModel):
    """KPI de besoin en fonds de roulement (Working Capital).

    Tous les délais sont en jours ; les montants en centimes.
    None signifie données insuffisantes pour calculer.
    """

    dso_days: float | None  # Délai moyen paiement client (Days Sales Outstanding)
    dpo_days: float | None  # Délai moyen paiement fournisseur (Days Payable Outstanding)
    bfr_cents: int | None  # Besoin en Fonds de Roulement (créances - dettes)
    receivables_cents: int  # créances clients en cours
    payables_cents: int  # dettes fournisseurs en cours
    matched_in_count: int  # nb d'engagements clients appariés (échantillon DSO)
    matched_out_count: int  # nb d'engagements fournisseurs appariés (échantillon DPO)
    has_data: bool  # False si aucun engagement saisi (état vide UI)


# ---------------------------------------------------------------------------
# 2. Top movers
# ---------------------------------------------------------------------------


class TopMoverRow(BaseModel):
    category_id: int
    label: str
    direction: Literal["in", "out"]
    delta_cents: int
    sparkline_3m_cents: list[int] = Field(default_factory=list)


class TopMoversResponse(BaseModel):
    increases: list[TopMoverRow]
    decreases: list[TopMoverRow]


# ---------------------------------------------------------------------------
# 3. Runway
# ---------------------------------------------------------------------------


class RunwayResponse(BaseModel):
    burn_rate_cents: int
    current_balance_cents: int
    runway_months: int | None
    forecast_balance_6m_cents: list[int]
    status: Literal["critical", "warning", "ok", "none"]


# ---------------------------------------------------------------------------
# 4. Year-over-year
# ---------------------------------------------------------------------------


class YoYPoint(BaseModel):
    month: str  # "YYYY-MM"
    revenues_current: int
    revenues_previous: int
    expenses_current: int
    expenses_previous: int


class YoYResponse(BaseModel):
    months: list[str]
    series: list[YoYPoint]


# ---------------------------------------------------------------------------
# 5. Client concentration
# ---------------------------------------------------------------------------


class ClientSlice(BaseModel):
    counterparty_id: int | None
    name: str
    amount_cents: int
    share_pct: float


class ClientConcentrationResponse(BaseModel):
    total_revenue_cents: int
    top5: list[ClientSlice]
    others_cents: int
    others_share_pct: float
    hhi: float
    risk_level: Literal["low", "medium", "high"]


# ---------------------------------------------------------------------------
# 6. Entities comparison
# ---------------------------------------------------------------------------


class EntityCompareRow(BaseModel):
    entity_id: int
    name: str
    revenues_cents: int
    expenses_cents: int
    net_variation_cents: int
    current_balance_cents: int
    burn_rate_cents: int
    runway_months: int | None


class EntitiesComparisonResponse(BaseModel):
    entities: list[EntityCompareRow]
