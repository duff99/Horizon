"""Schémas Pydantic pour le prévisionnel de trésorerie."""
from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ForecastRecurrence(str, enum.Enum):
    """Récurrence d'un flux prévisionnel (D1 : anciennement dans models/forecast_entry)."""
    NONE = "NONE"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY = "YEARLY"


class DetectedRecurrenceSuggestion(BaseModel):
    """Récurrence détectée automatiquement depuis l'historique des transactions."""
    model_config = ConfigDict(from_attributes=True)

    counterparty_id: int | None
    counterparty_name: str
    average_amount: Decimal
    last_occurrence: date
    next_expected: date
    recurrence: ForecastRecurrence
    occurrences_count: int
    entity_id: int


class ForecastProjectionPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    balance: Decimal
    # Apport net planifié le jour J (entries + récurrences, exclut les
    # transactions réelles déjà passées — la projection ne démarre qu'à today+1).
    planned_net: Decimal


class ForecastProjection(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    starting_balance: Decimal
    starting_date: date
    horizon_days: int
    points: list[ForecastProjectionPoint]


# ---------------------------------------------------------------------------
# Plan 5b — Scenarios + Lines (forecast v2)
# ---------------------------------------------------------------------------


class ForecastMethod(str, enum.Enum):
    """Méthodes de calcul d'une ligne prévisionnelle.

    Miroir de `app.models.forecast_line.ForecastLineMethod` côté API.
    """

    RECURRING_FIXED = "RECURRING_FIXED"
    SINGLE_MONTH_FIXED = "SINGLE_MONTH_FIXED"
    AVG_3M = "AVG_3M"
    AVG_6M = "AVG_6M"
    AVG_12M = "AVG_12M"
    PREVIOUS_MONTH = "PREVIOUS_MONTH"
    SAME_MONTH_LAST_YEAR = "SAME_MONTH_LAST_YEAR"
    BASED_ON_CATEGORY = "BASED_ON_CATEGORY"
    FORMULA = "FORMULA"


class ScenarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_id: int
    name: str
    description: str | None = None
    is_default: bool
    created_at: datetime


class ScenarioCreate(BaseModel):
    entity_id: int
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    is_default: bool = False


class ScenarioUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    is_default: bool | None = None


class LineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scenario_id: int
    entity_id: int
    category_id: int
    method: ForecastMethod
    amount_cents: int | None = None
    base_category_id: int | None = None
    ratio: Decimal | None = None
    formula_expr: str | None = None
    start_month: date | None = None
    end_month: date | None = None
    updated_at: datetime


class LineUpsert(BaseModel):
    scenario_id: int
    category_id: int
    method: ForecastMethod
    amount_cents: int | None = None
    base_category_id: int | None = None
    ratio: Decimal | None = Field(default=None, gt=0, le=10)
    formula_expr: str | None = None
    start_month: date | None = None
    end_month: date | None = None

    @model_validator(mode="after")
    def check_method_params(self) -> "LineUpsert":
        if self.method == ForecastMethod.RECURRING_FIXED and self.amount_cents is None:
            raise ValueError("RECURRING_FIXED requires amount_cents")
        if self.method == ForecastMethod.SINGLE_MONTH_FIXED and (
            self.amount_cents is None or self.start_month is None
        ):
            raise ValueError(
                "SINGLE_MONTH_FIXED requires amount_cents and start_month"
            )
        if self.method == ForecastMethod.BASED_ON_CATEGORY and (
            self.base_category_id is None or self.ratio is None
        ):
            raise ValueError("BASED_ON_CATEGORY requires base_category_id and ratio")
        if self.method == ForecastMethod.FORMULA and not self.formula_expr:
            raise ValueError("FORMULA requires formula_expr")
        if (
            self.start_month is not None
            and self.end_month is not None
            and self.start_month > self.end_month
        ):
            raise ValueError("start_month must be <= end_month")
        return self


class ValidateFormulaRequest(BaseModel):
    scenario_id: int
    formula_expr: str
    category_id: int | None = None


class ValidateFormulaResponse(BaseModel):
    valid: bool
    error: str | None = None


# ---------------------------------------------------------------------------
# Plan 5b Phase 5 — Pivot response
# ---------------------------------------------------------------------------


class PivotCellRead(BaseModel):
    """Cellule (catégorie, mois) du pivot prévisionnel."""

    month: str  # format "YYYY-MM"
    realized_cents: int
    committed_cents: int
    forecast_cents: int
    total_cents: int
    line_method: str | None = None
    line_params: dict | None = None
    insufficient_history: bool = False
    # True si la cellule mélange des montants au signe inattendu pour le
    # kind de sa catégorie (kind='in' avec une tx<0, ou kind='out' avec
    # une tx>0). Permet d'afficher un badge d'alerte côté UI.
    sign_anomaly: bool = False


class PivotRowRead(BaseModel):
    category_id: int
    parent_id: int | None = None
    label: str
    level: int
    direction: str  # "in" ou "out"
    cells: list[PivotCellRead]


class SeriesPointRead(BaseModel):
    month: str
    in_cents: int
    out_cents: int


class PivotResponse(BaseModel):
    months: list[str]
    opening_balance_cents: int
    closing_balance_projection_cents: list[int]
    rows: list[PivotRowRead]
    realized_series: list[SeriesPointRead]
    forecast_series: list[SeriesPointRead]
    # Net mensuel des transactions sans catégorie (inclus dans la
    # projection mais absent de `rows`). > 0 → l'UI peut afficher un
    # avertissement "Vous avez X € de transactions non catégorisées sur
    # cette période". Liste de la même longueur que `months`.
    uncategorized_net_cents: list[int] = []
