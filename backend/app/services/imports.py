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


from rapidfuzz import fuzz, process
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.counterparty import Counterparty, CounterpartyStatus

FUZZY_THRESHOLD = 90


def _normalize_counterparty_name(raw: str) -> str:
    # Uppercase, collapse whitespace. Dots are removed (not spaced) so that
    # "ACME S.A.S." normalizes to "ACME SAS" rather than "ACME S A S",
    # enabling the expected fuzzy match against stored "ACME SAS".
    import re
    cleaned = raw.upper().replace(".", "")
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    return " ".join(cleaned.split())


def match_or_create_counterparty(
    session: Session,
    *,
    entity_id: int,
    hint: str | None,
) -> tuple[Counterparty | None, bool]:
    """Retourne (Counterparty, was_created).

    - (None, False) si hint est vide.
    - (existing, False) si match fuzzy >= 90 % (token_set_ratio) sur
      `normalized_name` des contreparties de l'entité (statut != ignored).
    - (new, True) si aucune correspondance : création auto en statut `pending`.

    Le flag `was_created` permet au caller de compter uniquement les vraies
    créations (pas les pending pré-existantes matchées) dans
    `ImportRecord.counterparties_pending_created`.
    """
    if not hint or not hint.strip():
        return None, False

    clean = _normalize_counterparty_name(hint)

    existing = session.execute(
        select(Counterparty).where(
            Counterparty.entity_id == entity_id,
            Counterparty.status != CounterpartyStatus.IGNORED,
        )
    ).scalars().all()

    if existing:
        choices = {cp.id: cp.normalized_name for cp in existing}
        best = process.extractOne(
            clean, choices, scorer=fuzz.token_set_ratio
        )
        if best is not None and best[1] >= FUZZY_THRESHOLD:
            cp_id = best[2]
            return next(cp for cp in existing if cp.id == cp_id), False

    # Création auto-pending
    cp = Counterparty(
        entity_id=entity_id,
        name=clean,
        normalized_name=clean,
        status=CounterpartyStatus.PENDING,
    )
    session.add(cp)
    session.flush()
    return cp, True
