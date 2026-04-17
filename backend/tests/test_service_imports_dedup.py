"""Unicité de la dedup_key et détection de doublons."""
from datetime import date
from decimal import Decimal

from app.services.imports import compute_dedup_key, DedupKeyInput


ACC_ID = 1


def test_dedup_key_is_deterministic() -> None:
    payload = DedupKeyInput(
        bank_account_id=ACC_ID,
        operation_date=date(2026, 1, 10),
        value_date=date(2026, 1, 10),
        amount=Decimal("-42.50"),
        normalized_label="VIR SEPA ACME SAS",
        statement_row_index=3,
    )
    k1 = compute_dedup_key(payload)
    k2 = compute_dedup_key(payload)
    assert k1 == k2
    assert len(k1) == 64
    assert all(c in "0123456789abcdef" for c in k1)


def test_dedup_key_differs_if_amount_changes() -> None:
    base = DedupKeyInput(
        bank_account_id=ACC_ID,
        operation_date=date(2026, 1, 10),
        value_date=date(2026, 1, 10),
        amount=Decimal("-42.50"),
        normalized_label="VIR SEPA ACME SAS",
        statement_row_index=3,
    )
    other = DedupKeyInput(**{**base.__dict__, "amount": Decimal("-42.51")})
    assert compute_dedup_key(base) != compute_dedup_key(other)


def test_dedup_key_differs_if_row_index_changes() -> None:
    base = DedupKeyInput(
        bank_account_id=ACC_ID,
        operation_date=date(2026, 1, 10),
        value_date=date(2026, 1, 10),
        amount=Decimal("-42.50"),
        normalized_label="VIR SEPA ACME SAS",
        statement_row_index=3,
    )
    other = DedupKeyInput(**{**base.__dict__, "statement_row_index": 4})
    assert compute_dedup_key(base) != compute_dedup_key(other)
