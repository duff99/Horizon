"""Tests de /api/dashboard/summary."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.entity import Entity
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction, TransactionCategorizationSource


def _mk_import(
    db: Session,
    *,
    bank_account: BankAccount,
    closing: Decimal,
    period_end: date,
    status: ImportStatus = ImportStatus.COMPLETED,
) -> ImportRecord:
    ir = ImportRecord(
        bank_account_id=bank_account.id,
        bank_code=bank_account.bank_code,
        status=status,
        period_start=period_end.replace(day=1),
        period_end=period_end,
        opening_balance=Decimal("0"),
        closing_balance=closing,
        imported_count=0,
    )
    db.add(ir)
    db.flush()
    return ir


def _mk_tx(
    db: Session,
    *,
    bank_account: BankAccount,
    import_record: ImportRecord,
    op_date: date,
    amount: Decimal,
    row_idx: int,
    categorized_by: TransactionCategorizationSource = TransactionCategorizationSource.NONE,
    is_parent: bool = False,
) -> Transaction:
    tx = Transaction(
        bank_account_id=bank_account.id,
        import_id=import_record.id,
        operation_date=op_date,
        value_date=op_date,
        amount=amount,
        label=f"tx{row_idx}",
        raw_label=f"tx{row_idx}",
        dedup_key=f"dk-{bank_account.id}-{row_idx}-{op_date.isoformat()}",
        statement_row_index=row_idx,
        is_aggregation_parent=is_parent,
        normalized_label=f"tx{row_idx}",
        categorized_by=categorized_by,
    )
    db.add(tx)
    return tx


def test_summary_requires_auth(client: TestClient) -> None:
    r = client.get("/api/dashboard/summary")
    assert r.status_code == 401


def test_summary_empty_user_has_no_entities(
    client: TestClient, auth_user
) -> None:
    """User sans UserEntityAccess → tout à zéro, 200 OK."""
    r = client.get("/api/dashboard/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["total_balance"] == "0"
    assert body["inflows"] == "0"
    assert body["outflows"] == "0"
    assert body["uncategorized_count"] == 0
    assert body["daily"] == []
    assert body["total_balance_asof"] is None


def test_summary_current_month_aggregates(
    client: TestClient, auth_user_with_bank_account, db_session: Session
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    today = date.today()
    first = today.replace(day=1)
    ir = _mk_import(db_session, bank_account=ba, closing=Decimal("1234.56"), period_end=today)
    _mk_tx(db_session, bank_account=ba, import_record=ir, op_date=first, amount=Decimal("1000.00"), row_idx=1)
    _mk_tx(db_session, bank_account=ba, import_record=ir, op_date=first, amount=Decimal("-300.00"), row_idx=2)
    _mk_tx(
        db_session, bank_account=ba, import_record=ir, op_date=first,
        amount=Decimal("-100.00"), row_idx=3,
        categorized_by=TransactionCategorizationSource.MANUAL,
    )
    db_session.commit()

    r = client.get("/api/dashboard/summary?period=current_month")
    assert r.status_code == 200, r.text
    body = r.json()
    assert Decimal(body["inflows"]) == Decimal("1000.00")
    assert Decimal(body["outflows"]) == Decimal("-400.00")
    assert body["uncategorized_count"] == 2  # tx 1 + 2 sont NONE
    assert Decimal(body["total_balance"]) == Decimal("1234.56")
    assert body["total_balance_asof"] == today.isoformat()
    assert len(body["daily"]) >= 1


def test_summary_excludes_aggregation_parents(
    client: TestClient, auth_user_with_bank_account, db_session: Session
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    today = date.today()
    ir = _mk_import(db_session, bank_account=ba, closing=Decimal("0"), period_end=today)
    _mk_tx(
        db_session, bank_account=ba, import_record=ir, op_date=today,
        amount=Decimal("-9999.00"), row_idx=1, is_parent=True,
    )
    _mk_tx(
        db_session, bank_account=ba, import_record=ir, op_date=today,
        amount=Decimal("-50.00"), row_idx=2,
    )
    db_session.commit()

    r = client.get("/api/dashboard/summary?period=current_month")
    body = r.json()
    assert Decimal(body["outflows"]) == Decimal("-50.00")


def test_summary_previous_month_window(
    client: TestClient, auth_user_with_bank_account, db_session: Session
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    today = date.today()
    first_of_current = today.replace(day=1)
    last_of_prev = first_of_current - timedelta(days=1)
    ir = _mk_import(db_session, bank_account=ba, closing=Decimal("0"), period_end=today)
    _mk_tx(
        db_session, bank_account=ba, import_record=ir, op_date=last_of_prev,
        amount=Decimal("500.00"), row_idx=1,
    )
    _mk_tx(
        db_session, bank_account=ba, import_record=ir, op_date=today,
        amount=Decimal("999.00"), row_idx=2,
    )
    db_session.commit()

    r = client.get("/api/dashboard/summary?period=previous_month")
    body = r.json()
    assert Decimal(body["inflows"]) == Decimal("500.00")


@pytest.mark.skip(
    reason="Option C (2026-04) : admin a accès implicite à toutes les entités. "
    "auth_user_with_bank_account logue un admin → 200 désormais. À réécrire."
)
def test_summary_entity_id_forbidden_when_no_access(
    client: TestClient, auth_user_with_bank_account, db_session: Session
) -> None:
    other = Entity(name="Autre", legal_name="Autre SAS")
    db_session.add(other)
    db_session.commit()

    r = client.get(f"/api/dashboard/summary?entity_id={other.id}")
    assert r.status_code == 403


def test_summary_entity_id_filter_scopes_results(
    client: TestClient, auth_user_with_bank_account, db_session: Session
) -> None:
    accessible_entity = auth_user_with_bank_account["entity"]
    ba = auth_user_with_bank_account["bank_account"]
    today = date.today()
    ir = _mk_import(db_session, bank_account=ba, closing=Decimal("777"), period_end=today)
    _mk_tx(
        db_session, bank_account=ba, import_record=ir, op_date=today,
        amount=Decimal("100.00"), row_idx=1,
    )
    db_session.commit()

    r = client.get(f"/api/dashboard/summary?entity_id={accessible_entity.id}")
    assert r.status_code == 200
    body = r.json()
    assert Decimal(body["inflows"]) == Decimal("100.00")


def test_summary_invalid_period_rejected(
    client: TestClient, auth_user
) -> None:
    r = client.get("/api/dashboard/summary?period=foo")
    assert r.status_code == 422


def test_summary_total_balance_uses_latest_import(
    client: TestClient, auth_user_with_bank_account, db_session: Session
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    today = date.today()
    _mk_import(
        db_session, bank_account=ba,
        closing=Decimal("100"), period_end=today - timedelta(days=60),
    )
    _mk_import(
        db_session, bank_account=ba,
        closing=Decimal("500"), period_end=today - timedelta(days=30),
    )
    db_session.commit()

    r = client.get("/api/dashboard/summary")
    body = r.json()
    assert Decimal(body["total_balance"]) == Decimal("500")


def test_summary_daily_series_sorted(
    client: TestClient, auth_user_with_bank_account, db_session: Session
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    today = date.today()
    ir = _mk_import(db_session, bank_account=ba, closing=Decimal("0"), period_end=today)
    d1 = today.replace(day=1)
    d2 = d1 + timedelta(days=2)
    _mk_tx(db_session, bank_account=ba, import_record=ir, op_date=d2, amount=Decimal("10"), row_idx=1)
    _mk_tx(db_session, bank_account=ba, import_record=ir, op_date=d1, amount=Decimal("20"), row_idx=2)
    db_session.commit()

    r = client.get("/api/dashboard/summary?period=current_month")
    body = r.json()
    dates = [d["date"] for d in body["daily"]]
    assert dates == sorted(dates)


# ---------------------------------------------------------------------------
# /api/dashboard/bank-balances — Δ vs mois précédent (BUG-D-001)
# ---------------------------------------------------------------------------


def test_bank_balances_delta_uses_asof_not_calendar_today(
    client: TestClient, auth_user_with_bank_account, db_session: Session
) -> None:
    """Regression BUG-D-001 : le delta vs mois-1 doit utiliser le 1er du
    mois du dernier import du compte, pas le 1er du mois calendaire courant.

    Sinon, un compte dont le dernier import a period_end < today.replace(day=1)
    est comparé à lui-même → delta = 0.

    Setup : un compte avec 2 imports (mars 31 closing=7133.82,
    avril 30 closing=7933.72) et today situé en mai. Attendu : delta=+799.90.
    Avant le fix : delta=0.
    """
    ba = auth_user_with_bank_account["bank_account"]
    _mk_import(db_session, bank_account=ba, closing=Decimal("7133.82"), period_end=date(2026, 3, 31))
    _mk_import(db_session, bank_account=ba, closing=Decimal("7933.72"), period_end=date(2026, 4, 30))
    db_session.commit()

    r = client.get("/api/dashboard/bank-balances")
    assert r.status_code == 200, r.text
    rows = r.json()
    target = [row for row in rows if row["bank_account_id"] == ba.id]
    assert len(target) == 1, target
    assert Decimal(target[0]["balance"]) == Decimal("7933.72")
    assert target[0]["delta_vs_prev_month"] is not None
    assert Decimal(target[0]["delta_vs_prev_month"]) == Decimal("799.90"), (
        f"delta attendu +799.90, observé {target[0]['delta_vs_prev_month']}"
    )


def test_bank_balances_delta_none_when_no_previous_import(
    client: TestClient, auth_user_with_bank_account, db_session: Session
) -> None:
    """Un seul import (pas de mois précédent) → delta = None (pas 0)."""
    ba = auth_user_with_bank_account["bank_account"]
    _mk_import(db_session, bank_account=ba, closing=Decimal("1000.00"), period_end=date(2026, 4, 30))
    db_session.commit()

    r = client.get("/api/dashboard/bank-balances")
    rows = r.json()
    target = [row for row in rows if row["bank_account_id"] == ba.id][0]
    assert target["delta_vs_prev_month"] is None


def test_bank_balances_delta_per_account_no_cross_pollution(
    client: TestClient, auth_user_with_bank_account, db_session: Session
) -> None:
    """Regression BUG-D-001 deuxième partie : avec plusieurs comptes ayant
    des cutoffs différents, le delta de chaque compte ne doit pas être
    pollué par les dates d'un autre compte (produit cartésien IN()).
    """
    e = auth_user_with_bank_account["entity"]
    ba1 = auth_user_with_bank_account["bank_account"]
    ba2 = BankAccount(
        entity_id=e.id, bank_code="delubac", bank_name="Delubac",
        iban="FR76TEST2NDACCT" + "0" * 10, name="2nd Account",
    )
    db_session.add(ba2)
    db_session.flush()

    # ba1 : dernier import = avril 2026
    _mk_import(db_session, bank_account=ba1, closing=Decimal("100.00"), period_end=date(2026, 3, 31))
    _mk_import(db_session, bank_account=ba1, closing=Decimal("200.00"), period_end=date(2026, 4, 30))
    # ba2 : dernier import = mars 2026 (différent cutoff)
    _mk_import(db_session, bank_account=ba2, closing=Decimal("5000.00"), period_end=date(2026, 2, 28))
    _mk_import(db_session, bank_account=ba2, closing=Decimal("5500.00"), period_end=date(2026, 3, 31))
    db_session.commit()

    r = client.get("/api/dashboard/bank-balances")
    rows = {row["bank_account_id"]: row for row in r.json()}
    assert Decimal(rows[ba1.id]["delta_vs_prev_month"]) == Decimal("100.00"), "ba1 : 200 - 100 = 100"
    assert Decimal(rows[ba2.id]["delta_vs_prev_month"]) == Decimal("500.00"), "ba2 : 5500 - 5000 = 500"
