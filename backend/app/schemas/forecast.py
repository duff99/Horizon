"""Schémas Pydantic pour le prévisionnel de trésorerie."""
from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.forecast_entry import ForecastRecurrence


class ForecastEntryCreate(BaseModel):
    entity_id: int
    bank_account_id: int | None = None
    label: str = Field(min_length=1, max_length=255)
    amount: Decimal
    due_date: date
    category_id: int | None = None
    counterparty_id: int | None = None
    recurrence: ForecastRecurrence = ForecastRecurrence.NONE
    recurrence_until: date | None = None
    notes: str | None = None


class ForecastEntryUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=255)
    amount: Decimal | None = None
    due_date: date | None = None
    bank_account_id: int | None = None
    category_id: int | None = None
    counterparty_id: int | None = None
    recurrence: ForecastRecurrence | None = None
    recurrence_until: date | None = None
    notes: str | None = None


class ForecastEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_id: int
    bank_account_id: int | None
    label: str
    amount: Decimal
    due_date: date
    category_id: int | None
    counterparty_id: int | None
    recurrence: ForecastRecurrence
    recurrence_until: date | None
    notes: str | None


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
