"""Schemas Pydantic pour les anomalies p95 (G4)."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class AnomalyRow(BaseModel):
    transaction_id: int
    operation_date: date
    label: str
    amount_cents: int
    category_id: int | None
    category_label: str | None
    p95_cents: int  # seuil p95 de la catégorie sur les N jours analysés
    ratio: float    # abs(amount) / p95, ex: 2.3 = 2.3× le p95


class AnomalyResponse(BaseModel):
    entity_id: int
    days_analyzed: int
    anomaly_count: int
    rows: list[AnomalyRow]  # triées ratio desc
