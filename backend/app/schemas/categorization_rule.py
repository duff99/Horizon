"""Schémas Pydantic pour les règles de catégorisation."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.parsers.normalization import normalize_label


class RuleBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str = Field(min_length=1, max_length=120)
    entity_id: Optional[int] = None
    priority: int = Field(ge=1)

    label_operator: Optional[
        Literal["CONTAINS", "STARTS_WITH", "ENDS_WITH", "EQUALS"]
    ] = None
    label_value: Optional[str] = Field(default=None, max_length=200)
    direction: Literal["CREDIT", "DEBIT", "ANY"] = "ANY"
    amount_operator: Optional[
        Literal["EQ", "NE", "GT", "LT", "BETWEEN"]
    ] = None
    amount_value: Optional[Decimal] = None
    amount_value2: Optional[Decimal] = None
    counterparty_id: Optional[int] = None
    bank_account_id: Optional[int] = None
    category_id: int

    @field_validator("label_value")
    @classmethod
    def _normalize_label_value(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v2 = normalize_label(v)
        if not v2:
            raise ValueError("label_value vide après normalisation")
        return v2

    @model_validator(mode="after")
    def _check_filters_coherent(self) -> "RuleBase":
        has_filter = (
            self.label_operator is not None
            or self.counterparty_id is not None
            or self.bank_account_id is not None
            or self.amount_operator is not None
            or self.direction != "ANY"
        )
        if not has_filter:
            raise ValueError(
                "Au moins un filtre est requis (libellé, contrepartie, compte, "
                "montant ou sens non-ANY)."
            )

        if self.label_operator is not None and not self.label_value:
            raise ValueError("label_value requis si label_operator est fourni.")

        if self.amount_operator is not None and self.amount_value is None:
            raise ValueError("amount_value requis si amount_operator est fourni.")

        if self.amount_operator == "BETWEEN":
            if self.amount_value2 is None:
                raise ValueError("amount_value2 requis pour BETWEEN.")
            if self.amount_value is None or self.amount_value >= self.amount_value2:
                raise ValueError("amount_value doit être < amount_value2 pour BETWEEN.")

        return self


class RuleCreate(RuleBase):
    pass


class RuleUpdate(BaseModel):
    """Tous les champs optionnels — PATCH partiel."""
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    priority: Optional[int] = Field(default=None, ge=1)
    label_operator: Optional[
        Literal["CONTAINS", "STARTS_WITH", "ENDS_WITH", "EQUALS"]
    ] = None
    label_value: Optional[str] = None
    direction: Optional[Literal["CREDIT", "DEBIT", "ANY"]] = None
    amount_operator: Optional[Literal["EQ", "NE", "GT", "LT", "BETWEEN"]] = None
    amount_value: Optional[Decimal] = None
    amount_value2: Optional[Decimal] = None
    counterparty_id: Optional[int] = None
    bank_account_id: Optional[int] = None
    category_id: Optional[int] = None

    @field_validator("label_value")
    @classmethod
    def _normalize_label_value(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return normalize_label(v)


class RuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    entity_id: Optional[int]
    priority: int
    is_system: bool
    label_operator: Optional[str]
    label_value: Optional[str]
    direction: str
    amount_operator: Optional[str]
    amount_value: Optional[Decimal]
    amount_value2: Optional[Decimal]
    counterparty_id: Optional[int]
    bank_account_id: Optional[int]
    category_id: int
    created_at: datetime
    updated_at: datetime


class RulePreviewRequest(RuleBase):
    """Payload pour `/rules/preview` : une RuleCreate non persistée."""
    pass


class RuleSampleTransaction(BaseModel):
    id: int
    operation_date: str
    amount: Decimal
    label: str
    current_category_id: Optional[int]


class RulePreviewResponse(BaseModel):
    matching_count: int
    sample: list[RuleSampleTransaction]


class RuleApplyResponse(BaseModel):
    updated_count: int


class RuleSuggestion(BaseModel):
    """Retour de `/rules/from-transactions`."""
    suggested_label_operator: Literal["CONTAINS", "STARTS_WITH"]
    suggested_label_value: str
    suggested_direction: Literal["CREDIT", "DEBIT", "ANY"]
    suggested_bank_account_id: Optional[int]
    transaction_count: int


class RuleReorderItem(BaseModel):
    id: int
    priority: int


class BulkCategorizeRequest(BaseModel):
    transaction_ids: list[int] = Field(min_length=1)
    category_id: int
