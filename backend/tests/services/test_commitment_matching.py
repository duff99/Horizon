"""Tests du service commitment_matching : scoring + auto-match import."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.commitment import Commitment, CommitmentDirection, CommitmentStatus
from app.models.counterparty import Counterparty, CounterpartyStatus
from app.models.entity import Entity
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction
from app.models.user import User
from app.services.commitment_matching import (
    suggest_matches,
    suggest_matches_for_tx,
)


def _mk_entity_and_ba(db: Session, *, user: User | None = None) -> tuple[Entity, BankAccount]:
    e = Entity(name="Acme", legal_name="Acme SAS")
    db.add(e)
    db.flush()
    ba = BankAccount(
        entity_id=e.id,
        bank_code="delubac",
        bank_name="Delubac",
        iban=f"FR76{e.id:026d}"[:34],
        name="Compte",
    )
    db.add(ba)
    db.flush()
    return e, ba


def _mk_tx(
    db: Session,
    ba: BankAccount,
    *,
    amount: Decimal,
    op_date: date,
    label: str = "TX",
    counterparty: Counterparty | None = None,
) -> Transaction:
    # Besoin d'un ImportRecord parent
    rec = ImportRecord(
        bank_account_id=ba.id,
        bank_code="delubac",
        status=ImportStatus.COMPLETED,
    )
    db.add(rec)
    db.flush()
    tx = Transaction(
        bank_account_id=ba.id,
        import_id=rec.id,
        operation_date=op_date,
        value_date=op_date,
        amount=amount,
        label=label,
        raw_label=label,
        normalized_label=label.lower(),
        dedup_key=f"k-{label}-{op_date}-{amount}",
        statement_row_index=0,
        counterparty_id=counterparty.id if counterparty else None,
    )
    db.add(tx)
    db.flush()
    return tx


class TestSuggestMatches:
    def test_filters_by_entity_direction_and_date_window(
        self, db_session: Session,
    ) -> None:
        e, ba = _mk_entity_and_ba(db_session)
        c = Commitment(
            entity_id=e.id,
            direction=CommitmentDirection.OUT,
            amount_cents=15000,
            issue_date=date(2026, 4, 1),
            expected_date=date(2026, 4, 20),
            status=CommitmentStatus.PENDING,
        )
        db_session.add(c)
        db_session.flush()

        # In-window, OUT tx
        t_in = _mk_tx(
            db_session, ba,
            amount=Decimal("-150.00"),
            op_date=date(2026, 4, 19),
            label="Loyer",
        )
        # Out-of-window (too early)
        t_off = _mk_tx(
            db_session, ba,
            amount=Decimal("-150.00"),
            op_date=date(2026, 4, 10),
            label="Loyer ancien",
        )
        # Wrong direction (IN)
        t_wrong = _mk_tx(
            db_session, ba,
            amount=Decimal("150.00"),
            op_date=date(2026, 4, 20),
            label="Remb",
        )

        results = suggest_matches(db_session, c)
        tx_ids = {tx.id for tx, _ in results}
        assert t_in.id in tx_ids
        assert t_off.id not in tx_ids
        assert t_wrong.id not in tx_ids

    def test_score_prefers_exact_match(
        self, db_session: Session,
    ) -> None:
        e, ba = _mk_entity_and_ba(db_session)
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

        t_exact = _mk_tx(
            db_session, ba,
            amount=Decimal("-100.00"),
            op_date=date(2026, 4, 15),
            label="Exact",
        )
        t_far = _mk_tx(
            db_session, ba,
            amount=Decimal("-110.00"),
            op_date=date(2026, 4, 18),
            label="Far",
        )

        results = suggest_matches(db_session, c)
        # top result = exact
        assert results[0][0].id == t_exact.id
        assert results[0][1] > results[1][1]

    def test_counterparty_bonus(self, db_session: Session) -> None:
        e, ba = _mk_entity_and_ba(db_session)
        cp = Counterparty(
            entity_id=e.id, name="EDF", normalized_name="EDF",
            status=CounterpartyStatus.ACTIVE,
        )
        db_session.add(cp)
        db_session.flush()

        c = Commitment(
            entity_id=e.id,
            counterparty_id=cp.id,
            direction=CommitmentDirection.OUT,
            amount_cents=5000,
            issue_date=date(2026, 4, 1),
            expected_date=date(2026, 4, 15),
            status=CommitmentStatus.PENDING,
        )
        db_session.add(c)
        db_session.flush()

        t_cp = _mk_tx(
            db_session, ba,
            amount=Decimal("-52.00"),
            op_date=date(2026, 4, 15),
            label="EDF",
            counterparty=cp,
        )
        t_nocp = _mk_tx(
            db_session, ba,
            amount=Decimal("-50.00"),
            op_date=date(2026, 4, 15),
            label="Autre",
        )

        results = suggest_matches(db_session, c)
        # Counterparty bonus (+20) doit dépasser l'écart de 2 EUR
        assert results[0][0].id == t_cp.id

    def test_excludes_already_matched_transactions(
        self, db_session: Session,
    ) -> None:
        e, ba = _mk_entity_and_ba(db_session)
        c1 = Commitment(
            entity_id=e.id,
            direction=CommitmentDirection.OUT,
            amount_cents=5000,
            issue_date=date(2026, 4, 1),
            expected_date=date(2026, 4, 15),
            status=CommitmentStatus.PAID,
        )
        db_session.add(c1)
        db_session.flush()
        t = _mk_tx(
            db_session, ba,
            amount=Decimal("-50.00"),
            op_date=date(2026, 4, 15),
            label="Déjà lié",
        )
        c1.matched_transaction_id = t.id
        db_session.flush()

        c2 = Commitment(
            entity_id=e.id,
            direction=CommitmentDirection.OUT,
            amount_cents=5000,
            issue_date=date(2026, 4, 1),
            expected_date=date(2026, 4, 15),
            status=CommitmentStatus.PENDING,
        )
        db_session.add(c2)
        db_session.flush()

        results = suggest_matches(db_session, c2)
        assert all(tx.id != t.id for tx, _ in results)


class TestSuggestMatchesForTx:
    def test_returns_single_pending_commitment_above_threshold(
        self, db_session: Session,
    ) -> None:
        e, ba = _mk_entity_and_ba(db_session)
        c = Commitment(
            entity_id=e.id,
            direction=CommitmentDirection.OUT,
            amount_cents=5000,
            issue_date=date(2026, 4, 1),
            expected_date=date(2026, 4, 15),
            status=CommitmentStatus.PENDING,
        )
        db_session.add(c)
        db_session.flush()

        t = _mk_tx(
            db_session, ba,
            amount=Decimal("-50.00"),
            op_date=date(2026, 4, 15),
            label="Loyer",
        )
        result = suggest_matches_for_tx(db_session, t)
        assert result is not None
        assert result.id == c.id

    def test_returns_none_if_no_pending_match(
        self, db_session: Session,
    ) -> None:
        e, ba = _mk_entity_and_ba(db_session)
        t = _mk_tx(
            db_session, ba,
            amount=Decimal("-50.00"),
            op_date=date(2026, 4, 15),
            label="Orphelin",
        )
        assert suggest_matches_for_tx(db_session, t) is None

    def test_returns_none_if_ambiguous(
        self, db_session: Session,
    ) -> None:
        e, ba = _mk_entity_and_ba(db_session)
        for _ in range(2):
            c = Commitment(
                entity_id=e.id,
                direction=CommitmentDirection.OUT,
                amount_cents=5000,
                issue_date=date(2026, 4, 1),
                expected_date=date(2026, 4, 15),
                status=CommitmentStatus.PENDING,
            )
            db_session.add(c)
        db_session.flush()

        t = _mk_tx(
            db_session, ba,
            amount=Decimal("-50.00"),
            op_date=date(2026, 4, 15),
            label="Ambig",
        )
        # 2 pending commitments same score → ambiguous, no auto-link
        assert suggest_matches_for_tx(db_session, t) is None
