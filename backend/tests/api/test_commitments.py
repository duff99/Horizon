"""Tests API /api/commitments (CRUD + match/unmatch/suggest)."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.commitment import Commitment, CommitmentDirection, CommitmentStatus
from app.models.entity import Entity
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction
from app.models.user import User
from app.models.user_entity_access import UserEntityAccess


@pytest.fixture()
def entity_with_ba(db_session: Session, auth_user: User) -> dict:
    e = Entity(name="E1", legal_name="E1")
    db_session.add(e)
    db_session.flush()
    db_session.add(UserEntityAccess(user_id=auth_user.id, entity_id=e.id))
    ba = BankAccount(
        entity_id=e.id,
        bank_code="delubac",
        bank_name="Delubac",
        iban="FR7600000000000000000000111",
        name="Cpt",
    )
    db_session.add(ba)
    db_session.commit()
    db_session.refresh(ba)
    return {"entity": e, "bank_account": ba}


def _mk_tx(
    db: Session, ba: BankAccount, *, amount: Decimal, op_date: date, label: str = "t",
) -> Transaction:
    rec = ImportRecord(
        bank_account_id=ba.id, bank_code="delubac", status=ImportStatus.COMPLETED,
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
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


class TestCommitmentsCRUD:
    def test_create_list_get_patch_delete(
        self, client: TestClient, entity_with_ba: dict,
    ) -> None:
        e = entity_with_ba["entity"]
        payload = {
            "entity_id": e.id,
            "direction": "out",
            "amount_cents": 150000,
            "issue_date": "2026-04-01",
            "expected_date": "2026-04-20",
            "reference": "FAC-123",
            "description": "Loyer T1",
        }
        r = client.post("/api/commitments", json=payload)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["amount_cents"] == 150000
        assert body["status"] == "pending"
        cid = body["id"]

        r = client.get(f"/api/commitments?entity_id={e.id}")
        assert r.status_code == 200
        lst = r.json()
        assert lst["total"] == 1
        assert lst["items"][0]["id"] == cid

        r = client.get(f"/api/commitments/{cid}")
        assert r.status_code == 200
        assert r.json()["reference"] == "FAC-123"

        r = client.patch(
            f"/api/commitments/{cid}", json={"reference": "FAC-999"},
        )
        assert r.status_code == 200
        assert r.json()["reference"] == "FAC-999"

        r = client.delete(f"/api/commitments/{cid}")
        assert r.status_code == 204
        # Soft delete : status = cancelled
        r = client.get(f"/api/commitments/{cid}")
        assert r.status_code == 200
        assert r.json()["status"] == "cancelled"

    def test_create_requires_entity_access(
        self, client: TestClient, auth_user_reader: User, db_session: Session,
    ) -> None:
        other = Entity(name="X", legal_name="X")
        db_session.add(other)
        db_session.commit()

        r = client.post(
            "/api/commitments",
            json={
                "entity_id": other.id,
                "direction": "in",
                "amount_cents": 10000,
                "issue_date": "2026-04-01",
                "expected_date": "2026-04-10",
            },
        )
        assert r.status_code == 403

    def test_create_validates_dates(
        self, client: TestClient, entity_with_ba: dict,
    ) -> None:
        e = entity_with_ba["entity"]
        r = client.post(
            "/api/commitments",
            json={
                "entity_id": e.id,
                "direction": "out",
                "amount_cents": 1000,
                "issue_date": "2026-04-15",
                "expected_date": "2026-04-01",  # inversé
            },
        )
        assert r.status_code == 422

    def test_create_rejects_negative_amount(
        self, client: TestClient, entity_with_ba: dict,
    ) -> None:
        e = entity_with_ba["entity"]
        r = client.post(
            "/api/commitments",
            json={
                "entity_id": e.id,
                "direction": "out",
                "amount_cents": -100,
                "issue_date": "2026-04-01",
                "expected_date": "2026-04-15",
            },
        )
        assert r.status_code == 422

    def test_get_404_if_not_found(
        self, client: TestClient, auth_user: User,
    ) -> None:
        r = client.get("/api/commitments/99999")
        assert r.status_code == 404

    def test_get_403_if_entity_inaccessible(
        self, client: TestClient, auth_user_reader: User, db_session: Session,
    ) -> None:
        other = Entity(name="Y", legal_name="Y")
        db_session.add(other)
        db_session.flush()
        c = Commitment(
            entity_id=other.id,
            direction=CommitmentDirection.OUT,
            amount_cents=1000,
            issue_date=date(2026, 4, 1),
            expected_date=date(2026, 4, 15),
        )
        db_session.add(c)
        db_session.commit()

        r = client.get(f"/api/commitments/{c.id}")
        assert r.status_code == 403


class TestCommitmentMatch:
    def test_match_sets_status_paid(
        self, client: TestClient, entity_with_ba: dict, db_session: Session,
    ) -> None:
        e = entity_with_ba["entity"]
        ba = entity_with_ba["bank_account"]
        c = Commitment(
            entity_id=e.id,
            direction=CommitmentDirection.OUT,
            amount_cents=5000,
            issue_date=date(2026, 4, 1),
            expected_date=date(2026, 4, 15),
        )
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        tx = _mk_tx(
            db_session, ba, amount=Decimal("-50.00"),
            op_date=date(2026, 4, 15), label="Loyer",
        )

        r = client.post(
            f"/api/commitments/{c.id}/match", json={"transaction_id": tx.id},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "paid"
        assert body["matched_transaction_id"] == tx.id

    def test_match_conflict_if_tx_already_linked(
        self, client: TestClient, entity_with_ba: dict, db_session: Session,
    ) -> None:
        e = entity_with_ba["entity"]
        ba = entity_with_ba["bank_account"]
        tx = _mk_tx(
            db_session, ba, amount=Decimal("-50.00"),
            op_date=date(2026, 4, 15), label="Loyer",
        )
        c1 = Commitment(
            entity_id=e.id,
            direction=CommitmentDirection.OUT,
            amount_cents=5000,
            issue_date=date(2026, 4, 1),
            expected_date=date(2026, 4, 15),
            status=CommitmentStatus.PAID,
            matched_transaction_id=tx.id,
        )
        c2 = Commitment(
            entity_id=e.id,
            direction=CommitmentDirection.OUT,
            amount_cents=5000,
            issue_date=date(2026, 4, 1),
            expected_date=date(2026, 4, 15),
        )
        db_session.add_all([c1, c2])
        db_session.commit()

        r = client.post(
            f"/api/commitments/{c2.id}/match", json={"transaction_id": tx.id},
        )
        assert r.status_code == 409

    @pytest.mark.skip(
        reason="Option C (2026-04) : admin a accès implicite à toutes les entités. "
        "Ce test, basé sur un admin bloqué sur une autre entité, n'a plus de sens. "
        "À réécrire avec auth_user_reader + accès partiel pour vérifier la même "
        "garantie côté reader."
    )
    def test_match_forbidden_if_tx_inaccessible(
        self, client: TestClient, entity_with_ba: dict, db_session: Session,
    ) -> None:
        e = entity_with_ba["entity"]
        other = Entity(name="Z", legal_name="Z")
        db_session.add(other)
        db_session.flush()
        other_ba = BankAccount(
            entity_id=other.id, bank_code="delubac", bank_name="Delubac",
            iban="FR7699999999999999999999888", name="Other",
        )
        db_session.add(other_ba)
        db_session.flush()
        tx_other = _mk_tx(
            db_session, other_ba, amount=Decimal("-50.00"),
            op_date=date(2026, 4, 15), label="X",
        )

        c = Commitment(
            entity_id=e.id,
            direction=CommitmentDirection.OUT,
            amount_cents=5000,
            issue_date=date(2026, 4, 1),
            expected_date=date(2026, 4, 15),
        )
        db_session.add(c)
        db_session.commit()

        r = client.post(
            f"/api/commitments/{c.id}/match", json={"transaction_id": tx_other.id},
        )
        assert r.status_code == 403

    def test_unmatch_resets_to_pending(
        self, client: TestClient, entity_with_ba: dict, db_session: Session,
    ) -> None:
        e = entity_with_ba["entity"]
        ba = entity_with_ba["bank_account"]
        tx = _mk_tx(
            db_session, ba, amount=Decimal("-50.00"),
            op_date=date(2026, 4, 15), label="Loyer",
        )
        c = Commitment(
            entity_id=e.id,
            direction=CommitmentDirection.OUT,
            amount_cents=5000,
            issue_date=date(2026, 4, 1),
            expected_date=date(2026, 4, 15),
            status=CommitmentStatus.PAID,
            matched_transaction_id=tx.id,
        )
        db_session.add(c)
        db_session.commit()

        r = client.post(f"/api/commitments/{c.id}/unmatch")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "pending"
        assert body["matched_transaction_id"] is None


class TestCommitmentSuggestions:
    def test_suggest_matches_returns_candidates(
        self, client: TestClient, entity_with_ba: dict, db_session: Session,
    ) -> None:
        e = entity_with_ba["entity"]
        ba = entity_with_ba["bank_account"]
        c = Commitment(
            entity_id=e.id,
            direction=CommitmentDirection.OUT,
            amount_cents=5000,
            issue_date=date(2026, 4, 1),
            expected_date=date(2026, 4, 15),
        )
        db_session.add(c)
        db_session.commit()

        _mk_tx(
            db_session, ba, amount=Decimal("-50.00"),
            op_date=date(2026, 4, 15), label="Loyer",
        )
        r = client.get(f"/api/commitments/{c.id}/suggest-matches")
        assert r.status_code == 200
        body = r.json()
        assert len(body["candidates"]) >= 1
        assert body["candidates"][0]["label"] == "Loyer"
