"""Pipeline d'import : orchestre parser + normalisation + dedup + insertion."""
from __future__ import annotations

import os


class ImportLimitError(Exception):
    """Erreur générique de dépassement de limite."""


class FileTooLargeError(ImportLimitError):
    pass


class TooManyPagesError(ImportLimitError):
    pass


class TooManyTransactionsError(ImportLimitError):
    pass


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        v = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} doit être un entier, reçu : {raw!r}") from exc
    if v <= 0:
        raise RuntimeError(f"{name} doit être > 0")
    return v


MAX_BYTES = _env_int("IMPORT_MAX_BYTES", 20 * 1024 * 1024)
MAX_PAGES = _env_int("IMPORT_MAX_PAGES", 500)
MAX_TRANSACTIONS = _env_int("IMPORT_MAX_TRANSACTIONS", 10_000)
PARSE_TIMEOUT_S = _env_int("IMPORT_PARSE_TIMEOUT_S", 60)


def check_size_limit(data: bytes, *, max_bytes: int = MAX_BYTES) -> None:
    if len(data) > max_bytes:
        raise FileTooLargeError(
            f"Fichier de {len(data)} octets > limite {max_bytes}"
        )


def check_pages_limit(*, pages: int, max_pages: int = MAX_PAGES) -> None:
    if pages > max_pages:
        raise TooManyPagesError(f"{pages} pages > limite {max_pages}")


def check_transactions_limit(*, count: int, max_count: int = MAX_TRANSACTIONS) -> None:
    if count > max_count:
        raise TooManyTransactionsError(
            f"{count} transactions > limite {max_count}"
        )


import hashlib
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class DedupKeyInput:
    bank_account_id: int
    operation_date: date
    value_date: date
    amount: Decimal
    normalized_label: str
    statement_row_index: int


def compute_dedup_key(payload: DedupKeyInput) -> str:
    """Retourne le SHA-256 hex (64 caractères) déterministe de l'entrée."""
    # Montant en centimes signé, stable : évite les pièges Decimal("-42.50") vs "-42.5"
    amount_cents = int((payload.amount * 100).to_integral_value())
    parts = [
        str(payload.bank_account_id),
        payload.operation_date.isoformat(),
        payload.value_date.isoformat(),
        str(amount_cents),
        payload.normalized_label,
        str(payload.statement_row_index),
    ]
    blob = "|".join(parts).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()
