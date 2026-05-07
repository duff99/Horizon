"""Schemas Pydantic pour les endpoints drift-acks (G12 — snooze de dérive)."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class DriftSnoozeRequest(BaseModel):
    entity_id: int
    category_id: int
    snooze_days: int = 30
    note: str | None = None


class DriftAckRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    entity_id: int
    category_id: int
    snoozed_until: date
    acknowledged_at: datetime
    acknowledged_by_id: int | None
    note: str | None
