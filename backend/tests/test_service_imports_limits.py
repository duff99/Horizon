"""Les limites du pipeline d'import doivent rejeter les fichiers trop gros."""
import pytest

from app.services.imports import (
    FileTooLargeError,
    TooManyPagesError,
    TooManyTransactionsError,
    check_size_limit,
    check_pages_limit,
    check_transactions_limit,
)


def test_size_limit_accepts_small_file() -> None:
    check_size_limit(b"x" * 100, max_bytes=1024)


def test_size_limit_rejects_large_file() -> None:
    with pytest.raises(FileTooLargeError):
        check_size_limit(b"x" * 2048, max_bytes=1024)


def test_pages_limit_accepts_within_bound() -> None:
    check_pages_limit(pages=10, max_pages=500)


def test_pages_limit_rejects_over_bound() -> None:
    with pytest.raises(TooManyPagesError):
        check_pages_limit(pages=501, max_pages=500)


def test_transactions_limit_rejects_over_bound() -> None:
    with pytest.raises(TooManyTransactionsError):
        check_transactions_limit(count=10_001, max_count=10_000)
