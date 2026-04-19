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
