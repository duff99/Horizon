"""Tests API /api/dashboard/month-comparison (Plan 5b Phase 5)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.entity import Entity
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction
from app.models.user import User
from app.models.user_entity_access import UserEntityAccess


_FR_MONTHS_ABBR = (
    "janv.", "févr.", "mars", "avr.", "mai", "juin",
    "juil.", "août", "sept.", "oct.", "nov.", "déc.",
)


def _previous_first(first_of: date) -> date:
    if first_of.month == 1:
        return date(first_of.year - 1, 12, 1)
    return date(first_of.year, first_of.month - 1, 1)


@pytest.fixture()
def mc_ctx(db_session: Session, auth_user: User) -> dict:
    """Entité accessible avec un compte bancaire + ImportRecord placeholder."""
    e = Entity(name="EMonthCmp", legal_name="EMonthCmp")
    db_session.add(e)
    db_session.flush()
    db_session.add(UserEntityAccess(user_id=auth_user.id, entity_id=e.id))
    ba = BankAccount(
        entity_id=e.id,
        bank_code="delubac",
        bank_name="Delubac",
        iban="FR7600000000000000000000811",
        name="Compte MC",
    )
    db_session.add(ba)
    db_session.flush()
    ir = ImportRecord(
        bank_account_id=ba.id,
        bank_code="delubac",
        filename="mc.pdf",
        status=ImportStatus.COMPLETED,
        imported_count=0,
    )
    db_session.add(ir)
    db_session.commit()
    db_session.refresh(e)
    db_session.refresh(ba)
    db_session.refresh(ir)
    return {"entity": e, "bank_account": ba, "import_record": ir}


def _add_tx(
    db: Session,
    *,
    ba: BankAccount,
    ir: ImportRecord,
    op: date,
    amount: Decimal,
    idx: int,
) -> None:
    db.add(
        Transaction(
            bank_account_id=ba.id,
            import_id=ir.id,
            operation_date=op,
            value_date=op,
            amount=amount,
            label=f"tx {idx}",
            raw_label=f"tx {idx}",
            dedup_key=f"mc-{ba.id}-{idx}-{op.isoformat()}",
            statement_row_index=idx,
            normalized_label=f"tx {idx}",
        )
    )


class TestMonthComparison:
    def test_happy_path(
        self, client: TestClient, mc_ctx: dict, db_session: Session
    ) -> None:
        today = date.today()
        cur_first = today.replace(day=1)
        prev_first = _previous_first(cur_first)
        ba = mc_ctx["bank_account"]
        ir = mc_ctx["import_record"]
        # Mois courant : +145.00 / -138.00
        _add_tx(db_session, ba=ba, ir=ir, op=cur_first, amount=Decimal("145.00"), idx=1)
        _add_tx(db_session, ba=ba, ir=ir, op=cur_first, amount=Decimal("-138.00"), idx=2)
        # Mois précédent : +147.635 / -120.703
        _add_tx(db_session, ba=ba, ir=ir, op=prev_first, amount=Decimal("147.63"), idx=3)
        _add_tx(db_session, ba=ba, ir=ir, op=prev_first, amount=Decimal("-120.70"), idx=4)
        db_session.commit()

        r = client.get("/api/dashboard/month-comparison")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["current"]["in_cents"] == 14_500
        assert body["current"]["out_cents"] == -13_800
        assert body["previous"]["in_cents"] == 14_763
        assert body["previous"]["out_cents"] == -12_070
        expected_cur = f"{_FR_MONTHS_ABBR[cur_first.month - 1]} {cur_first.year}"
        expected_prev = f"{_FR_MONTHS_ABBR[prev_first.month - 1]} {prev_first.year}"
        assert body["current"]["month_label"] == expected_cur
        assert body["previous"]["month_label"] == expected_prev

    def test_entity_filter(
        self, client: TestClient, mc_ctx: dict, db_session: Session, auth_user: User
    ) -> None:
        # Crée une 2ème entité accessible + compte, avec des mouvements cur month
        today = date.today()
        cur_first = today.replace(day=1)
        e2 = Entity(name="EMonthCmp2", legal_name="EMonthCmp2")
        db_session.add(e2)
        db_session.flush()
        db_session.add(UserEntityAccess(user_id=auth_user.id, entity_id=e2.id))
        ba2 = BankAccount(
            entity_id=e2.id,
            bank_code="delubac",
            bank_name="Delubac",
            iban="FR7600000000000000000000822",
            name="Compte MC2",
        )
        db_session.add(ba2)
        db_session.flush()
        ir2 = ImportRecord(
            bank_account_id=ba2.id,
            bank_code="delubac",
            filename="mc2.pdf",
            status=ImportStatus.COMPLETED,
            imported_count=0,
        )
        db_session.add(ir2)
        db_session.flush()
        _add_tx(
            db_session, ba=mc_ctx["bank_account"], ir=mc_ctx["import_record"],
            op=cur_first, amount=Decimal("100.00"), idx=11,
        )
        _add_tx(db_session, ba=ba2, ir=ir2, op=cur_first, amount=Decimal("900.00"), idx=12)
        db_session.commit()

        r_all = client.get("/api/dashboard/month-comparison")
        r_e1 = client.get(
            f"/api/dashboard/month-comparison?entity_id={mc_ctx['entity'].id}"
        )
        r_e2 = client.get(f"/api/dashboard/month-comparison?entity_id={e2.id}")
        assert r_all.status_code == 200
        assert r_e1.status_code == 200
        assert r_e2.status_code == 200
        assert r_all.json()["current"]["in_cents"] == 100_000
        assert r_e1.json()["current"]["in_cents"] == 10_000
        assert r_e2.json()["current"]["in_cents"] == 90_000

    @pytest.mark.skip(
        reason="Option C (2026-04) : admin a accès implicite à toutes les entités. "
        "mc_ctx logue un admin → 200 désormais. À réécrire avec auth_user_reader."
    )
    def test_forbidden_entity(
        self, client: TestClient, mc_ctx: dict, db_session: Session
    ) -> None:
        other = Entity(name="MCForeign", legal_name="MCForeign")
        db_session.add(other)
        db_session.commit()
        r = client.get(f"/api/dashboard/month-comparison?entity_id={other.id}")
        assert r.status_code == 403

    def test_empty_returns_zeros(
        self, client: TestClient, mc_ctx: dict
    ) -> None:
        # Aucune transaction seedée → toutes sommes à 0, labels non vides
        r = client.get("/api/dashboard/month-comparison")
        assert r.status_code == 200
        body = r.json()
        assert body["current"]["in_cents"] == 0
        assert body["current"]["out_cents"] == 0
        assert body["previous"]["in_cents"] == 0
        assert body["previous"]["out_cents"] == 0
        assert body["current"]["month_label"]
        assert body["previous"]["month_label"]
