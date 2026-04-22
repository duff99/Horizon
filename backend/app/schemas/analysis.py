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
