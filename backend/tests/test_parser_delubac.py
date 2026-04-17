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


def test_parse_minimal_transactions_count(parser: DelubacParser) -> None:
    stmt = parser.parse(_load("synthetic_minimal.pdf"))
    assert stmt.total_count == 3


def test_parse_minimal_transactions_content(parser: DelubacParser) -> None:
    stmt = parser.parse(_load("synthetic_minimal.pdf"))
    t0, t1, t2 = stmt.transactions
    # ARRETE DE COMPTE
    assert t0.operation_date == date(2026, 3, 2)
    assert t0.value_date == date(2026, 3, 1)
    assert "ARRETE DE COMPTE" in t0.label
    assert t0.amount == Decimal("-92.32")
    # COTIS CARTE
    assert t1.amount == Decimal("-80.00")
    assert "COTIS CARTE" in t1.label
    # VIR SEPA BNP PARIBAS FACTOR (crédit)
    assert t2.amount == Decimal("25204.95")
    assert "BNP PARIBAS FACTOR" in t2.label


def test_parse_ignores_page_totals_and_headers(parser: DelubacParser) -> None:
    stmt = parser.parse(_load("synthetic_full_month.pdf"))
    for t in stmt.transactions:
        # Aucune transaction ne doit contenir "Total des opérations" dans son libellé
        assert "Total des opérations" not in t.label
        assert "RELEVÉ DE COMPTE" not in t.label
        assert "Ancien solde" not in t.label
        assert "Nouveau solde" not in t.label


def test_parse_full_month_transactions_count_within_tolerance(parser: DelubacParser) -> None:
    """≥ 95% d'extraction vs vérité terrain."""
    import json
    stmt = parser.parse(_load("synthetic_full_month.pdf"))
    gt = json.loads((FIXTURES / "synthetic_full_month.ground_truth.json")
                    .read_text(encoding="utf-8"))
    expected = len(gt["transactions"])  # parents uniquement (enfants exposés via children)
    # total_count compte parents + enfants. Pour comparer avec gt,
    # on compte les "blocs" (parents du point de vue de la vérité terrain).
    actual_blocks = len(stmt.transactions)
    ratio = actual_blocks / expected
    assert ratio >= 0.95, f"Extraction insuffisante: {actual_blocks}/{expected} = {ratio:.1%}"
