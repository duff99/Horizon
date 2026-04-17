"""Tests des schémas Pydantic pour les règles."""
import pytest
from decimal import Decimal
from pydantic import ValidationError

from app.schemas.categorization_rule import (
    RuleCreate, RuleUpdate, RuleRead, RulePreviewRequest, RulePreviewResponse,
    RuleSuggestion, BulkCategorizeRequest, RuleReorderItem,
)


def test_rule_create_normalizes_label_value() -> None:
    r = RuleCreate(
        name="URSSAF", priority=1000,
        label_operator="CONTAINS", label_value="  Urssaf ",
        direction="ANY", category_id=1,
    )
    assert r.label_value == "URSSAF"


def test_rule_create_rejects_empty_filter_set() -> None:
    with pytest.raises(ValidationError):
        RuleCreate(
            name="Vide", priority=1000,
            direction="ANY", category_id=1,
        )


def test_rule_create_rejects_between_without_value2() -> None:
    with pytest.raises(ValidationError):
        RuleCreate(
            name="X", priority=1000,
            direction="DEBIT", category_id=1,
            amount_operator="BETWEEN", amount_value=Decimal("10"),
        )


def test_rule_create_rejects_between_with_inverted_values() -> None:
    with pytest.raises(ValidationError):
        RuleCreate(
            name="X", priority=1000,
            direction="DEBIT", category_id=1,
            amount_operator="BETWEEN",
            amount_value=Decimal("100"), amount_value2=Decimal("50"),
        )


def test_rule_create_label_operator_requires_value() -> None:
    with pytest.raises(ValidationError):
        RuleCreate(
            name="X", priority=1000,
            label_operator="CONTAINS",
            direction="ANY", category_id=1,
        )


def test_rule_preview_response_shape() -> None:
    resp = RulePreviewResponse(matching_count=42, sample=[])
    assert resp.matching_count == 42


def test_bulk_categorize_request_requires_ids() -> None:
    with pytest.raises(ValidationError):
        BulkCategorizeRequest(transaction_ids=[], category_id=1)
