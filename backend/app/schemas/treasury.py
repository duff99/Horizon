"""Schémas Pydantic pour les endpoints trésorerie (G1, G10)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# G1 — Solde quotidien 90 jours
# ---------------------------------------------------------------------------

class DailyBalancePoint(BaseModel):
    date: date
    balance: Decimal


class DailyBalanceResponse(BaseModel):
    entity_id: int
    days: int
    points: list[DailyBalancePoint]
    latest_balance: Decimal | None
    latest_date: date | None


# ---------------------------------------------------------------------------
# G10 — Position par compte bancaire
# ---------------------------------------------------------------------------

class PerAccountBalance(BaseModel):
    account_id: int
    account_name: str
    bank_name: str
    iban_last4: str
    balance_cents: int
    balance_30d_ago_cents: int | None
    variation_30d_cents: int | None
    last_import_date: date | None
    sparkline: list[int]


class PerAccountBalanceResponse(BaseModel):
    entity_id: int | None
    accounts: list[PerAccountBalance]


# ---------------------------------------------------------------------------
# G2 — Rolling 13-week
# ---------------------------------------------------------------------------

class Rolling13WPoint(BaseModel):
    week_label: str        # "2026-W18"
    week_start: date       # lundi de la semaine
    realized_cents: int    # Σ transactions réalisées (négatif = débit net)
    forecast_cents: int    # Σ forecast_lines (montants en centimes)
    is_past: bool          # True si week_start < today


class Rolling13WResponse(BaseModel):
    entity_id: int
    scenario_id: int | None
    points: list[Rolling13WPoint]  # 13 points : W-1 à W+11
