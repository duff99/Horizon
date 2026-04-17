"""Tests de la hiérarchie d'erreurs des parsers."""
import pytest

from app.parsers.errors import (
    InvalidPdfStructureError,
    ParserError,
    UnknownBankError,
)


def test_parser_error_is_exception() -> None:
    with pytest.raises(ParserError):
        raise ParserError("boom")


def test_unknown_bank_is_parser_error() -> None:
    with pytest.raises(ParserError):
        raise UnknownBankError()


def test_invalid_pdf_structure_carries_context() -> None:
    err = InvalidPdfStructureError("colonnes absentes", page=3)
    assert err.page == 3
    assert "page=3" in repr(err)
