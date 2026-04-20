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


from datetime import datetime, timezone

from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction
from app.parsers.base import ParsedStatement, ParsedTransaction
from app.parsers.normalization import normalize_label
from app.services.categorization import categorize_transaction


def _to_dedup_input(
    tx: ParsedTransaction,
    *,
    bank_account_id: int,
    label_suffix: str = "",
) -> DedupKeyInput:
    return DedupKeyInput(
        bank_account_id=bank_account_id,
        operation_date=tx.operation_date,
        value_date=tx.value_date,
        amount=tx.amount,
        normalized_label=tx.label + label_suffix,
        statement_row_index=tx.statement_row_index,
    )


def _flatten(parent: ParsedTransaction) -> list[ParsedTransaction]:
    out = [parent]
    out.extend(parent.children)
    return out


def ingest_parsed_statement(
    session: Session,
    *,
    bank_account_id: int,
    statement: ParsedStatement,
    override_duplicates: bool = False,
    import_record: ImportRecord | None = None,
) -> ImportRecord:
    """Insère atomiquement un ParsedStatement. Retourne l'ImportRecord mis à jour."""
    from app.models.bank_account import BankAccount

    ba = session.get(BankAccount, bank_account_id)
    if ba is None:
        raise ValueError(f"BankAccount {bank_account_id} introuvable")

    if import_record is None:
        import_record = ImportRecord(
            bank_account_id=bank_account_id,
            bank_code=statement.bank_code,
            status=ImportStatus.PENDING,
            period_start=statement.period_start,
            period_end=statement.period_end,
        )
        session.add(import_record)
        session.flush()

    overridden: list[str] = []
    pending_created = 0

    try:
        # 1. Aplatit tous les ParsedTransaction (parents + enfants)
        all_parsed: list[tuple[ParsedTransaction, bool]] = []
        for root in statement.transactions:
            for tx in _flatten(root):
                is_parent = tx is root and bool(root.children)
                all_parsed.append((tx, is_parent))

        # 2. Calcule les dedup_keys
        keys_to_check = [
            compute_dedup_key(_to_dedup_input(tx, bank_account_id=bank_account_id))
            for tx, _ in all_parsed
        ]

        # 3. Détecte les doublons existants en base
        existing_keys: set[str] = set(
            session.execute(
                select(Transaction.dedup_key).where(
                    Transaction.dedup_key.in_(keys_to_check)
                )
            ).scalars().all()
        )

        # 4. Insertion
        inserted_map: dict[int, Transaction] = {}
        imported_count = 0
        duplicates_skipped = 0

        def _insert_tx(
            tx: ParsedTransaction,
            parent_db: Transaction | None,
            is_aggregation_parent: bool,
        ) -> None:
            nonlocal imported_count, duplicates_skipped, pending_created
            key = compute_dedup_key(_to_dedup_input(tx, bank_account_id=bank_account_id))
            if key in existing_keys:
                if override_duplicates:
                    suffix = f"|dup:{datetime.now(timezone.utc).timestamp()}"
                    key = compute_dedup_key(
                        _to_dedup_input(
                            tx, bank_account_id=bank_account_id, label_suffix=suffix,
                        )
                    )
                    overridden.append(key)
                else:
                    duplicates_skipped += 1
                    return

            cp, was_created = match_or_create_counterparty(
                session, entity_id=ba.entity_id, hint=tx.counterparty_hint,
            )
            if was_created:
                pending_created += 1

            db_tx = Transaction(
                bank_account_id=bank_account_id,
                import_id=import_record.id,
                operation_date=tx.operation_date,
                value_date=tx.value_date,
                label=tx.label,
                raw_label=tx.raw_label,
                normalized_label=normalize_label(tx.label),
                amount=tx.amount,
                dedup_key=key,
                statement_row_index=tx.statement_row_index,
                is_aggregation_parent=is_aggregation_parent,
                parent_transaction_id=parent_db.id if parent_db else None,
                counterparty_id=cp.id if cp else None,
            )
            session.add(db_tx)
            session.flush()
            inserted_map[id(tx)] = db_tx
            imported_count += 1
            existing_keys.add(key)

        for root in statement.transactions:
            parent_db: Transaction | None = None
            if root.children:
                _insert_tx(root, None, is_aggregation_parent=True)
                parent_db = inserted_map.get(id(root))
                for child in root.children:
                    _insert_tx(child, parent_db, is_aggregation_parent=False)
            else:
                _insert_tx(root, None, is_aggregation_parent=False)

        # 5. Auto-catégorisation des transactions insérées (Plan 2 — Phase D)
        session.flush()
        categorized_count = 0
        for db_tx in inserted_map.values():
            matched = categorize_transaction(
                session, db_tx, entity_id=ba.entity_id,
            )
            if matched is not None:
                categorized_count += 1

        import_record.status = ImportStatus.COMPLETED
        import_record.imported_count = imported_count
        import_record.duplicates_skipped = duplicates_skipped
        import_record.counterparties_pending_created = pending_created
        import_record.opening_balance = statement.opening_balance
        import_record.closing_balance = statement.closing_balance
        audit: dict = {"categorized_count": categorized_count}
        if overridden:
            audit["overridden"] = overridden
        import_record.audit = audit
        session.flush()
        return import_record

    except Exception as exc:
        import_record.status = ImportStatus.FAILED
        import_record.error_message = str(exc)[:500]
        session.flush()
        raise


from app.parsers import get_parser_for
from app.parsers.errors import ParserError


def import_pdf_bytes(
    session: Session,
    *,
    bank_account_id: int,
    pdf_bytes: bytes,
    filename: str,
    override_duplicates: bool = False,
    uploaded_by_id: int | None = None,
) -> ImportRecord:
    check_size_limit(pdf_bytes)

    file_sha256 = hashlib.sha256(pdf_bytes).hexdigest()

    # Pré-crée le record pour pouvoir logger un échec de parsing
    rec = ImportRecord(
        bank_account_id=bank_account_id,
        uploaded_by_id=uploaded_by_id,
        bank_code="unknown",
        status=ImportStatus.PENDING,
        filename=filename,
        file_sha256=file_sha256,
        file_size_bytes=len(pdf_bytes),
        override_duplicates=override_duplicates,
    )
    session.add(rec)
    session.flush()

    try:
        parser = get_parser_for(pdf_bytes)
        rec.bank_code = parser.bank_code
        statement = parser.parse(pdf_bytes)
        rec.period_start = statement.period_start
        rec.period_end = statement.period_end
        check_pages_limit(pages=statement.page_count)
        check_transactions_limit(
            count=sum(1 + len(t.children) for t in statement.transactions)
        )
    except ParserError as exc:
        rec.status = ImportStatus.FAILED
        rec.error_message = str(exc)[:500]
        session.flush()
        raise

    return ingest_parsed_statement(
        session,
        bank_account_id=bank_account_id,
        statement=statement,
        override_duplicates=override_duplicates,
        import_record=rec,
    )
