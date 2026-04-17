"""Tests du registre des parsers."""
import pytest

from app.parsers import BaseParser, get_parser_for, get_registry, register_parser
from app.parsers.errors import UnknownBankError


class _FakeBank(BaseParser):
    bank_name = "Fake"
    bank_code = "fake"
    def detect(self, pdf_bytes: bytes) -> bool:
        return pdf_bytes.startswith(b"FAKE")
    def parse(self, pdf_bytes: bytes):  # type: ignore[override]
        raise NotImplementedError


@pytest.fixture(autouse=True)
def _snapshot_registry():
    backup = dict(get_registry())
    yield
    get_registry().clear()
    get_registry().update(backup)


def test_register_and_get_by_code() -> None:
    register_parser(_FakeBank())
    reg = get_registry()
    assert "fake" in reg
    assert isinstance(reg["fake"], _FakeBank)


def test_register_same_code_twice_raises() -> None:
    register_parser(_FakeBank())
    with pytest.raises(ValueError, match="already registered"):
        register_parser(_FakeBank())


def test_get_parser_for_detects() -> None:
    register_parser(_FakeBank())
    p = get_parser_for(b"FAKE content")
    assert isinstance(p, _FakeBank)


def test_get_parser_for_unknown_raises() -> None:
    register_parser(_FakeBank())
    with pytest.raises(UnknownBankError):
        get_parser_for(b"OTHER content")


def test_get_parser_by_code() -> None:
    from app.parsers import get_parser_by_code
    register_parser(_FakeBank())
    p = get_parser_by_code("fake")
    assert isinstance(p, _FakeBank)
    with pytest.raises(UnknownBankError):
        get_parser_by_code("nonexistent")
