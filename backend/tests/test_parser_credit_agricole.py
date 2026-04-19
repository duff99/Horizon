"""Tests du parser Crédit Agricole.

Les PDFs réels (documents-test/4.pdf…9.pdf) sont gitignored car ils contiennent
des données bancaires réelles. Ces tests vérifient donc uniquement le nom/code
du parser, la détection sur marqueurs, et les helpers de parsing statique.
La validation E2E se fait via script manuel sur les PDFs réels (voir README).
"""
from datetime import date
from decimal import Decimal

import pytest

from app.parsers.credit_agricole import CreditAgricoleParser


@pytest.fixture
def parser() -> CreditAgricoleParser:
    return CreditAgricoleParser()


def test_bank_code_and_name(parser: CreditAgricoleParser) -> None:
    assert parser.bank_code == "credit_agricole"
    assert parser.bank_name == "Crédit Agricole"


def test_detect_requires_pdf_header(parser: CreditAgricoleParser) -> None:
    assert parser.detect(b"not a pdf") is False


def test_detect_matches_credit_agricole_marker(parser: CreditAgricoleParser) -> None:
    pdf_head = b"%PDF-1.4\n" + b"CREDIT AGRICOLE" + b"\n" + b"x" * 100
    assert parser.detect(pdf_head) is True


def test_detect_matches_agrifrpp_bic(parser: CreditAgricoleParser) -> None:
    pdf_head = b"%PDF-1.4\nBIC : AGRIFRPP845\n" + b"x" * 100
    assert parser.detect(pdf_head) is True


def test_detect_rejects_unrelated_pdf(parser: CreditAgricoleParser) -> None:
    pdf_head = b"%PDF-1.4\nsome other bank\n" + b"x" * 100
    # Pas de marqueur : detect() tombe dans pdfplumber.open() qui lèvera → False
    assert parser.detect(pdf_head) is False


def test_parse_arrete_extracts_year_month(parser: CreditAgricoleParser) -> None:
    text = "... Date d'arrêté : 31 Janvier 2026 ..."
    year, month = parser._parse_arrete(text)
    assert year == 2026
    assert month == 1


def test_parse_arrete_month_names(parser: CreditAgricoleParser) -> None:
    cases = [
        ("Date d'arrêté : 15 Février 2026", (2026, 2)),
        ("Date d'arrêté : 1 Mars 2026", (2026, 3)),
        ("Date d'arrêté : 30 Avril 2025", (2025, 4)),
        ("Date d'arrêté : 31 Décembre 2025", (2025, 12)),
    ]
    for text, expected in cases:
        assert parser._parse_arrete(text) == expected


def test_parse_account_identifiers(parser: CreditAgricoleParser) -> None:
    text = (
        "Compte Courant n° 00925382647\n"
        "IBAN : FR76 1450 6002 6800 9253 8264 706 BIC : AGRIFRPP845"
    )
    acct, iban = parser._parse_account_identifiers(text)
    assert acct == "00925382647"
    assert iban == "FR7614506002680092538264706"


def test_parse_opening_balance_crediteur(parser: CreditAgricoleParser) -> None:
    text = "Ancien solde créditeur au 31.12.2025 1 000,00"
    amt, d = parser._parse_opening_balance(text)
    assert amt == Decimal("1000.00")
    assert d == date(2025, 12, 31)


def test_parse_opening_balance_debiteur_is_negative(parser: CreditAgricoleParser) -> None:
    text = "Ancien solde débiteur au 31.01.2026 45,85"
    amt, d = parser._parse_opening_balance(text)
    assert amt == Decimal("-45.85")
    assert d == date(2026, 1, 31)


def test_parse_closing_balance_crediteur(parser: CreditAgricoleParser) -> None:
    text = "Nouveau solde créditeur au 31.01.2026 374,80"
    amt, d = parser._parse_closing_balance(text)
    assert amt == Decimal("374.80")
    assert d == date(2026, 1, 31)


def test_short_date_same_year(parser: CreditAgricoleParser) -> None:
    # Txn dans le mois de l'arrêté (janvier) → année arrêté
    assert parser._short_date_to_date("15.01", year=2026, stmt_month=1) == date(2026, 1, 15)


def test_short_date_previous_year(parser: CreditAgricoleParser) -> None:
    # Txn du 31.12 sur un relevé de janvier 2026 → 31.12.2025
    assert parser._short_date_to_date("31.12", year=2026, stmt_month=1) == date(2025, 12, 31)
