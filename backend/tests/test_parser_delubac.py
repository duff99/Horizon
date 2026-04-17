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
