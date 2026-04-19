"""Schémas pour l'endpoint tableau de bord."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class DashboardPeriod(StrEnum):
    CURRENT_MONTH = "current_month"
    PREVIOUS_MONTH = "previous_month"
    LAST_30D = "last_30d"
    LAST_90D = "last_90d"


class DailyCashflow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    inflows: Decimal
    outflows: Decimal


class DashboardSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    period: DashboardPeriod
    period_label: str
    period_start: date
    period_end: date
    total_balance: Decimal
    total_balance_asof: date | None
    inflows: Decimal
    outflows: Decimal
    uncategorized_count: int
    daily: list[DailyCashflow]
