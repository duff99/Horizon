"""Tests de l'analyseur Delubac."""
from pathlib import Path

import pytest

from app.parsers.delubac import DelubacParser

FIXTURES = Path(__file__).parent / "fixtures" / "delubac"


@pytest.fixture
def parser() -> DelubacParser:
    return DelubacParser()


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_detect_delubac_minimal(parser: DelubacParser) -> None:
    assert parser.detect(_load("synthetic_minimal.pdf")) is True


def test_detect_delubac_full(parser: DelubacParser) -> None:
    assert parser.detect(_load("synthetic_full_month.pdf")) is True


def test_detect_non_delubac(parser: DelubacParser) -> None:
    # Bytes aléatoires en-tête PDF minimum
    assert parser.detect(b"%PDF-1.4\n1 0 obj <<>> endobj\n%%EOF\n") is False


def test_bank_code_and_name(parser: DelubacParser) -> None:
    assert parser.bank_code == "delubac"
    assert parser.bank_name == "Delubac"


from datetime import date
from decimal import Decimal


def test_parse_minimal_account_header(parser: DelubacParser) -> None:
    stmt = parser.parse(_load("synthetic_minimal.pdf"))
    assert stmt.bank_code == "delubac"
    assert stmt.iban == "FR7612879000011117020200105"
    assert stmt.account_number == "11170202001"
    assert stmt.opening_balance == Decimal("19.70")
    assert stmt.closing_balance == Decimal("25052.33")


def test_parse_minimal_period(parser: DelubacParser) -> None:
    stmt = parser.parse(_load("synthetic_minimal.pdf"))
    assert stmt.period_start == date(2026, 3, 2)
    assert stmt.period_end == date(2026, 3, 5)


def test_parse_full_month_period(parser: DelubacParser) -> None:
    stmt = parser.parse(_load("synthetic_full_month.pdf"))
    assert stmt.period_start == date(2026, 3, 2)
    assert stmt.period_end == date(2026, 3, 31)
    assert stmt.closing_balance == Decimal("33427.90")
