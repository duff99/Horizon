"""Schémas Pydantic pour le prévisionnel de trésorerie."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

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
