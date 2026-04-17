"""Tests des dataclasses ParsedTransaction et ParsedStatement."""
from datetime import date
from decimal import Decimal

import pytest

from app.parsers.base import ParsedStatement, ParsedTransaction


def test_parsed_transaction_signed_amount() -> None:
    t = ParsedTransaction(
        operation_date=date(2026, 3, 5),
        value_date=date(2026, 3, 5),
        label="COTIS CARTE",
        raw_label="COTIS CARTE",
        amount=Decimal("-80.00"),
        statement_row_index=3,
    )
    assert t.is_debit is True
    assert t.is_credit is False
    assert t.children == []


def test_parsed_transaction_children() -> None:
    child = ParsedTransaction(
        operation_date=date(2026, 3, 6),
        value_date=date(2026, 3, 6),
        label="COMMISSION VIR SEPA X",
        raw_label="COMMISSION VIR SEPA X",
        amount=Decimal("-0.50"),
        statement_row_index=2,
    )
    parent = ParsedTransaction(
        operation_date=date(2026, 3, 6),
        value_date=date(2026, 3, 6),
        label="VIR SEPA X",
        raw_label="VIR SEPA X",
        amount=Decimal("-1.50"),
        statement_row_index=1,
        children=[child],
    )
    assert parent.is_aggregation_parent is True
    assert child.is_aggregation_parent is False


def test_parsed_statement_total_count() -> None:
    p1 = ParsedTransaction(date(2026, 3, 1), date(2026, 3, 1),
                           "L1", "L1", Decimal("10"), 0)
    p2 = ParsedTransaction(date(2026, 3, 2), date(2026, 3, 2),
                           "L2", "L2", Decimal("-20"), 1)
    s = ParsedStatement(
        bank_code="delubac", account_number="123",
        iban="FR76XXX", period_start=date(2026, 3, 1),
        period_end=date(2026, 3, 2),
        opening_balance=Decimal("100"),
        closing_balance=Decimal("90"),
        transactions=[p1, p2],
    )
    assert s.total_count == 2
    assert s.bank_code == "delubac"


def test_parsed_statement_total_count_with_children() -> None:
    child = ParsedTransaction(date(2026, 3, 6), date(2026, 3, 6),
                              "c", "c", Decimal("-1"), 1)
    parent = ParsedTransaction(date(2026, 3, 6), date(2026, 3, 6),
                               "p", "p", Decimal("-2"), 0, children=[child])
    s = ParsedStatement(
        bank_code="delubac", account_number="1",
        iban="FR", period_start=date(2026, 3, 1),
        period_end=date(2026, 3, 6),
        opening_balance=Decimal("0"),
        closing_balance=Decimal("-2"),
        transactions=[parent],
    )
    # 1 parent + 1 enfant = 2 lignes logiques
    assert s.total_count == 2
