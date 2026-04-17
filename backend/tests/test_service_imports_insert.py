"""Insertion atomique : dedup, doublons, override, parent/enfants."""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.counterparty import Counterparty, CounterpartyStatus
from app.models.entity import Entity
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction
from app.parsers.base import ParsedStatement, ParsedTransaction
from app.services.imports import ingest_parsed_statement


def _fx_parent_child() -> ParsedStatement:
    parent = ParsedTransaction(
        operation_date=date(2026, 1, 10),
        value_date=date(2026, 1, 10),
        label="VIR SEPA ACME",
        raw_label="VIR SEPA ACME",
        amount=Decimal("-100.00"),
        statement_row_index=0,
        counterparty_hint="ACME",
    )
    child_comm = ParsedTransaction(
        operation_date=date(2026, 1, 10),
        value_date=date(2026, 1, 10),
        label="COMMISSION VIR SEPA ACME",
        raw_label="COMMISSION VIR SEPA ACME",
        amount=Decimal("-1.50"),
        statement_row_index=1,
    )
    parent.children.append(child_comm)
    return ParsedStatement(
        bank_code="delubac",
        iban="FR7600000000000000000000001",
        account_number="001",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        opening_balance=Decimal("1000.00"),
        closing_balance=Decimal("898.50"),
        transactions=[parent],
        page_count=1,
    )


def _fx_bank_account(session: Session) -> tuple[BankAccount, Entity]:
    e = Entity(name="SAS Test", legal_name="SAS Test SARL")
    session.add(e)
    session.flush()
    ba = BankAccount(
        entity_id=e.id,
        bank_code="delubac",
        bank_name="Delubac",
        iban="FR7600000000000000000000001",
        name="Compte courant",
    )
    session.add(ba)
    session.flush()
    return ba, e


def test_ingest_inserts_parent_and_children(db_session: Session) -> None:
    ba, _ = _fx_bank_account(db_session)
    stmt = _fx_parent_child()
    rec = ingest_parsed_statement(
        db_session, bank_account_id=ba.id, statement=stmt
    )
    assert rec.status == ImportStatus.COMPLETED
    assert rec.imported_count == 2
    assert rec.duplicates_skipped == 0

    rows = db_session.execute(select(Transaction)).scalars().all()
    assert len(rows) == 2
    parent = next(r for r in rows if r.amount == Decimal("-100.00"))
    child = next(r for r in rows if r.amount == Decimal("-1.50"))
    assert parent.is_aggregation_parent is True
    assert child.parent_transaction_id == parent.id


def test_ingest_skips_duplicates_by_default(db_session: Session) -> None:
    ba, _ = _fx_bank_account(db_session)
    stmt = _fx_parent_child()
    first = ingest_parsed_statement(db_session, bank_account_id=ba.id, statement=stmt)
    assert first.imported_count == 2
    # Second import de la même donnée
    second = ingest_parsed_statement(db_session, bank_account_id=ba.id, statement=stmt)
    assert second.imported_count == 0
    assert second.duplicates_skipped == 2


def test_ingest_override_duplicates_inserts_with_suffix(db_session: Session) -> None:
    ba, _ = _fx_bank_account(db_session)
    stmt = _fx_parent_child()
    ingest_parsed_statement(db_session, bank_account_id=ba.id, statement=stmt)
    rec = ingest_parsed_statement(
        db_session, bank_account_id=ba.id, statement=stmt, override_duplicates=True
    )
    assert rec.imported_count == 2
    assert rec.duplicates_skipped == 0
    # Plan bug: original asserts `"dup" in <sha256 hex>` which is unreliable.
    # Fixed to verify the actual intent: override dedup_keys are recorded in audit.
    assert rec.audit is not None
    assert len(rec.audit.get("overridden", [])) == 2


def test_ingest_creates_pending_counterparty(db_session: Session) -> None:
    ba, e = _fx_bank_account(db_session)
    stmt = _fx_parent_child()
    rec = ingest_parsed_statement(db_session, bank_account_id=ba.id, statement=stmt)
    cps = db_session.execute(
        select(Counterparty).where(Counterparty.entity_id == e.id)
    ).scalars().all()
    assert len(cps) == 1
    assert cps[0].name == "ACME"
    assert cps[0].status == CounterpartyStatus.PENDING
    assert rec.counterparties_pending_created == 1
