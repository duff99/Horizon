"""Tests pour les nouveaux endpoints d'analyse (drill-down, variance, BFR)."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.category import Category
from app.models.commitment import (
    Commitment,
    CommitmentDirection,
    CommitmentStatus,
)
from app.models.entity import Entity
from app.models.forecast_entry import ForecastEntry
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction
from app.models.user import User


def _today_first():
    return date.today().replace(day=1)


def _add_months(d: date, months: int) -> date:
    total = d.year * 12 + (d.month - 1) + months
    return date(total // 12, total % 12 + 1, 1)


def _mk_entity_with_ba(db: Session, user: User, name: str = "TestCo"):
    from app.models.user_entity_access import UserEntityAccess
    e = Entity(name=name, legal_name=name)
    db.add(e); db.flush()
    db.add(UserEntityAccess(user_id=user.id, entity_id=e.id))
    ba = BankAccount(
        entity_id=e.id, bank_code="delubac", bank_name="Delubac",
        iban=f"FR76{abs(hash(name)) % 10**22:022d}", name="Compte test",
    )
    db.add(ba); db.commit()
    db.refresh(ba)
    return e, ba


def _mk_tx(db, ba, *, amount, op_date, label="x", category_id=None):
    rec = ImportRecord(
        bank_account_id=ba.id, bank_code="delubac",
        status=ImportStatus.COMPLETED,
    )
    db.add(rec); db.flush()
    tx = Transaction(
        bank_account_id=ba.id, import_id=rec.id,
        operation_date=op_date, value_date=op_date,
        amount=amount, label=label, raw_label=label,
        normalized_label=label.lower(),
        category_id=category_id,
        dedup_key=f"k-{op_date}-{label}-{amount}-{rec.id}",
        statement_row_index=0,
    )
    db.add(tx); db.commit(); db.refresh(tx)
    return tx


# ---------------------------------------------------------------------------
# 1. Category-drift drill-down
# ---------------------------------------------------------------------------


def test_drift_detail_returns_current_month_transactions(
    client: TestClient, auth_user_admin: User, db_session: Session
):
    e, ba = _mk_entity_with_ba(db_session, auth_user_admin, "DriftCo")
    cat = Category(name="Loyer", slug="loyer-test", is_system=False)
    db_session.add(cat); db_session.commit()

    today = date.today()
    cm = today.replace(day=1)
    # 2 transactions ce mois, 1 le mois précédent (ne doit pas apparaître)
    _mk_tx(db_session, ba, amount=Decimal("-500"), op_date=cm, label="Loyer juin", category_id=cat.id)
    _mk_tx(db_session, ba, amount=Decimal("-250"), op_date=cm, label="Charges", category_id=cat.id)
    _mk_tx(db_session, ba, amount=Decimal("-500"), op_date=_add_months(cm, -1), label="Loyer mai", category_id=cat.id)

    resp = client.get(
        f"/api/analysis/category-drift/{cat.id}/transactions?entity_id={e.id}"
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["category_id"] == cat.id
    assert body["category_label"] == "Loyer"
    assert len(body["transactions"]) == 2
    # Tri par |amount| desc → Loyer juin (500) avant Charges (250)
    assert body["transactions"][0]["label"] == "Loyer juin"
    assert body["total_cents"] == -75000


def test_drift_detail_requires_entity_access(
    client: TestClient, auth_user_reader: User, db_session: Session
):
    other = Entity(name="OtherCo", legal_name="OtherCo")
    db_session.add(other); db_session.commit()
    cat = Category(name="x", slug="x-test", is_system=False)
    db_session.add(cat); db_session.commit()
    resp = client.get(
        f"/api/analysis/category-drift/{cat.id}/transactions?entity_id={other.id}"
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 2. Forecast variance
# ---------------------------------------------------------------------------


def test_forecast_variance_empty_when_no_forecast(
    client: TestClient, auth_user_admin: User, db_session: Session
):
    e, _ = _mk_entity_with_ba(db_session, auth_user_admin, "EmptyForecastCo")
    resp = client.get(f"/api/analysis/forecast-variance?entity_id={e.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["has_forecast"] is False
    assert len(body["points"]) == 6  # 6 mois par défaut
    for p in body["points"]:
        assert p["forecasted_cents"] == 0


def test_forecast_variance_compares_realized_vs_forecast(
    client: TestClient, auth_user_admin: User, db_session: Session
):
    e, ba = _mk_entity_with_ba(db_session, auth_user_admin, "VarianceCo")
    cm = _today_first()
    db_session.add(ForecastEntry(
        entity_id=e.id, label="Salaires prévus",
        amount=Decimal("-10000"), due_date=cm,
    ))
    db_session.commit()
    _mk_tx(db_session, ba, amount=Decimal("-9500"), op_date=cm, label="Salaires réels")
    _mk_tx(db_session, ba, amount=Decimal("-300"), op_date=cm, label="Frais")

    resp = client.get(f"/api/analysis/forecast-variance?entity_id={e.id}&months=3")
    assert resp.status_code == 200
    body = resp.json()
    assert body["has_forecast"] is True
    current_pt = body["points"][-1]  # dernier = mois courant
    assert current_pt["forecasted_cents"] == -1_000_000
    assert current_pt["actual_cents"] == -980_000
    assert current_pt["delta_cents"] == 20_000  # actual - forecast


# ---------------------------------------------------------------------------
# 3. Working capital (DSO/DPO/BFR)
# ---------------------------------------------------------------------------


def test_working_capital_empty_when_no_commitments(
    client: TestClient, auth_user_admin: User, db_session: Session
):
    e, _ = _mk_entity_with_ba(db_session, auth_user_admin, "EmptyWcCo")
    resp = client.get(f"/api/analysis/working-capital?entity_id={e.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["has_data"] is False
    assert body["dso_days"] is None
    assert body["dpo_days"] is None
    assert body["bfr_cents"] is None


def test_working_capital_returns_outstanding_amounts(
    client: TestClient, auth_user_admin: User, db_session: Session
):
    e, _ = _mk_entity_with_ba(db_session, auth_user_admin, "WcCo")
    today = date.today()
    # 2 créances pending (clients à encaisser)
    db_session.add_all([
        Commitment(
            entity_id=e.id, direction=CommitmentDirection.IN,
            amount_cents=300_000, issue_date=today - timedelta(days=10),
            expected_date=today + timedelta(days=20),
            status=CommitmentStatus.PENDING,
        ),
        Commitment(
            entity_id=e.id, direction=CommitmentDirection.IN,
            amount_cents=200_000, issue_date=today - timedelta(days=5),
            expected_date=today + timedelta(days=25),
            status=CommitmentStatus.PENDING,
        ),
    ])
    # 1 dette pending
    db_session.add(Commitment(
        entity_id=e.id, direction=CommitmentDirection.OUT,
        amount_cents=150_000, issue_date=today,
        expected_date=today + timedelta(days=30),
        status=CommitmentStatus.PENDING,
    ))
    db_session.commit()

    resp = client.get(f"/api/analysis/working-capital?entity_id={e.id}")
    body = resp.json()
    assert body["has_data"] is True
    assert body["receivables_cents"] == 500_000
    assert body["payables_cents"] == 150_000
    assert body["bfr_cents"] == 350_000
    # DSO/DPO None car < 3 commitments matched (samples insuffisants)
    assert body["dso_days"] is None


def test_working_capital_dso_when_enough_matched(
    client: TestClient, auth_user_admin: User, db_session: Session
):
    e, ba = _mk_entity_with_ba(db_session, auth_user_admin, "DsoCo")
    today = date.today()
    # 4 commitments client matched avec délais 10, 20, 30, 20 jours → moy 20
    for delay in (10, 20, 30, 20):
        issue = today - timedelta(days=delay + 5)
        paid = issue + timedelta(days=delay)
        tx = _mk_tx(db_session, ba, amount=Decimal("100"), op_date=paid, label=f"pay-{delay}")
        db_session.add(Commitment(
            entity_id=e.id, direction=CommitmentDirection.IN,
            amount_cents=10_000, issue_date=issue,
            expected_date=issue + timedelta(days=15),
            status=CommitmentStatus.PAID,
            matched_transaction_id=tx.id,
        ))
    db_session.commit()

    resp = client.get(f"/api/analysis/working-capital?entity_id={e.id}")
    body = resp.json()
    assert body["has_data"] is True
    assert body["matched_in_count"] == 4
    assert body["dso_days"] == 20.0
