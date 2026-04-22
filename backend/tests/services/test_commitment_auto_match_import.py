"""Test d'intégration : auto-match d'un commitment pending lors de l'import."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.commitment import Commitment, CommitmentDirection, CommitmentStatus
from app.models.entity import Entity
from app.parsers.base import ParsedStatement, ParsedTransaction
from app.services.imports import ingest_parsed_statement


def _fx_bank_account(session: Session) -> tuple[BankAccount, Entity]:
    e = Entity(name="SAS AutoMatch", legal_name="SAS AutoMatch")
    session.add(e)
    session.flush()
    ba = BankAccount(
        entity_id=e.id,
        bank_code="delubac",
        bank_name="Delubac",
        iban="FR7600000000000000000000042",
        name="Compte",
    )
    session.add(ba)
    session.flush()
    return ba, e


def test_ingest_auto_matches_pending_commitment(db_session: Session) -> None:
    ba, e = _fx_bank_account(db_session)
    c = Commitment(
        entity_id=e.id,
        direction=CommitmentDirection.OUT,
        amount_cents=10000,  # 100 EUR
        issue_date=date(2026, 4, 1),
        expected_date=date(2026, 4, 15),
        status=CommitmentStatus.PENDING,
    )
    db_session.add(c)
    db_session.flush()
    commitment_id = c.id

    stmt = ParsedStatement(
        bank_code="delubac",
        iban=ba.iban,
        account_number="042",
        period_start=date(2026, 4, 1),
        period_end=date(2026, 4, 30),
        opening_balance=Decimal("1000.00"),
        closing_balance=Decimal("900.00"),
        transactions=[
            ParsedTransaction(
                operation_date=date(2026, 4, 15),
                value_date=date(2026, 4, 15),
                label="PAIEMENT FOURN",
                raw_label="PAIEMENT FOURN",
                amount=Decimal("-100.00"),
                statement_row_index=0,
            )
        ],
        page_count=1,
    )

    rec = ingest_parsed_statement(
        db_session, bank_account_id=ba.id, statement=stmt,
    )
    assert rec.imported_count == 1

    db_session.refresh(c)
    assert c.status == CommitmentStatus.PAID
    assert c.matched_transaction_id is not None


def test_ingest_does_not_link_when_outside_window(
    db_session: Session,
) -> None:
    ba, e = _fx_bank_account(db_session)
    c = Commitment(
        entity_id=e.id,
        direction=CommitmentDirection.OUT,
        amount_cents=10000,
        issue_date=date(2026, 4, 1),
        expected_date=date(2026, 4, 15),
        status=CommitmentStatus.PENDING,
    )
    db_session.add(c)
    db_session.flush()

    stmt = ParsedStatement(
        bank_code="delubac",
        iban=ba.iban,
        account_number="042",
        period_start=date(2026, 5, 1),
        period_end=date(2026, 5, 30),
        opening_balance=Decimal("900.00"),
        closing_balance=Decimal("800.00"),
        transactions=[
            ParsedTransaction(
                operation_date=date(2026, 5, 20),  # hors fenêtre ±7j
                value_date=date(2026, 5, 20),
                label="PAIEMENT LOIN",
                raw_label="PAIEMENT LOIN",
                amount=Decimal("-100.00"),
                statement_row_index=0,
            )
        ],
        page_count=1,
    )
    ingest_parsed_statement(
        db_session, bank_account_id=ba.id, statement=stmt,
    )
    db_session.refresh(c)
    assert c.status == CommitmentStatus.PENDING
    assert c.matched_transaction_id is None
