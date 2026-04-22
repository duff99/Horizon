"""Schémas Pydantic pour les engagements (commitments)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.commitment import CommitmentDirection, CommitmentStatus


class CommitmentCreate(BaseModel):
    entity_id: int
    counterparty_id: int | None = None
    category_id: int | None = None
    bank_account_id: int | None = None
    direction: Literal["in", "out"]
    amount_cents: int = Field(gt=0, description="Montant en centimes, positif")
    issue_date: date
    expected_date: date
    reference: str | None = Field(default=None, max_length=255)
    description: str | None = None
    pdf_attachment_id: int | None = None

    @model_validator(mode="after")
    def _validate_dates(self) -> "CommitmentCreate":
        if self.issue_date > self.expected_date:
            raise ValueError(
                "issue_date doit être <= expected_date"
            )
        delta = (self.expected_date - self.issue_date).days
        if delta > 365:
            raise ValueError(
                "L'écart entre issue_date et expected_date ne doit pas dépasser 365 jours"
            )
        return self


class CommitmentUpdate(BaseModel):
    counterparty_id: int | None = None
    category_id: int | None = None
    bank_account_id: int | None = None
    direction: Literal["in", "out"] | None = None
    amount_cents: int | None = Field(default=None, gt=0)
    issue_date: date | None = None
    expected_date: date | None = None
    status: Literal["pending", "paid", "cancelled"] | None = None
    reference: str | None = Field(default=None, max_length=255)
    description: str | None = None
    pdf_attachment_id: int | None = None


class CommitmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_id: int
    counterparty_id: int | None
    counterparty_name: str | None = None
    category_id: int | None
    category_name: str | None = None
    bank_account_id: int | None
    direction: CommitmentDirection
    amount_cents: int
    issue_date: date
    expected_date: date
    status: CommitmentStatus
    matched_transaction_id: int | None
    reference: str | None
    description: str | None
    pdf_attachment_id: int | None
    created_by_id: int | None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def _populate_nested_names(cls, data):
        # Accept ORM object or dict.
        if hasattr(data, "counterparty") or hasattr(data, "category"):
            cp = getattr(data, "counterparty", None)
            cat = getattr(data, "category", None)
            values = {
                "id": data.id,
                "entity_id": data.entity_id,
                "counterparty_id": data.counterparty_id,
                "counterparty_name": cp.name if cp is not None else None,
                "category_id": data.category_id,
                "category_name": cat.name if cat is not None else None,
                "bank_account_id": data.bank_account_id,
                "direction": data.direction,
                "amount_cents": data.amount_cents,
                "issue_date": data.issue_date,
                "expected_date": data.expected_date,
                "status": data.status,
                "matched_transaction_id": data.matched_transaction_id,
                "reference": data.reference,
                "description": data.description,
                "pdf_attachment_id": data.pdf_attachment_id,
                "created_by_id": data.created_by_id,
                "created_at": data.created_at,
                "updated_at": data.updated_at,
            }
            return values
        return data


class CommitmentListResponse(BaseModel):
    items: list[CommitmentRead]
    total: int
    page: int
    per_page: int


class CommitmentMatchRequest(BaseModel):
    transaction_id: int


class TransactionBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    operation_date: date
    label: str
    amount: Decimal
    bank_account_label: str | None = None


class CommitmentSuggestionResponse(BaseModel):
    candidates: list[TransactionBrief]
