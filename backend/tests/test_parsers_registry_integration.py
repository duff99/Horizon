"""Vérifie que DelubacParser est bien enregistré à l'import du package."""
from pathlib import Path

from app.parsers import get_parser_by_code, get_parser_for
from app.parsers.delubac import DelubacParser

FIXTURES = Path(__file__).parent / "fixtures" / "delubac"


def test_delubac_registered_by_code() -> None:
    p = get_parser_by_code("delubac")
    assert isinstance(p, DelubacParser)


def test_delubac_autodetected_from_bytes() -> None:
    pdf = (FIXTURES / "synthetic_minimal.pdf").read_bytes()
    p = get_parser_for(pdf)
    assert isinstance(p, DelubacParser)
