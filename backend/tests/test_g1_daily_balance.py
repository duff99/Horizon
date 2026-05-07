"""Tests pour GET /api/treasury/daily-balance (G1)."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.entity import Entity
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction, TransactionCategorizationSource
from app.models.user_entity_access import UserEntityAccess
from app.models.user import User


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
) -> Transaction:
    tx = Transaction(
        bank_account_id=bank_account.id,
        import_id=import_record.id,
        operation_date=op_date,
        value_date=op_date,
        amount=amount,
        label=f"tx-g1-{row_idx}",
        raw_label=f"tx-g1-{row_idx}",
        dedup_key=f"dk-g1-{bank_account.id}-{row_idx}-{op_date.isoformat()}",
        statement_row_index=row_idx,
        is_aggregation_parent=False,
        normalized_label=f"tx-g1-{row_idx}",
        categorized_by=TransactionCategorizationSource.NONE,
    )
    db.add(tx)
    return tx


# ---------------------------------------------------------------------------
# Cas 1 : entité sans import → points=[]
# ---------------------------------------------------------------------------

def test_daily_balance_empty_no_import(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """Entité avec un compte bancaire mais aucun import → points vides."""
    entity = Entity(name="G1 Empty Entity", legal_name="G1 Empty Entity")
    db_session.add(entity)
    db_session.flush()
    access = UserEntityAccess(user_id=auth_user.id, entity_id=entity.id)
    ba = BankAccount(
        entity_id=entity.id,
        bank_code="delubac",
        bank_name="Delubac",
        iban="FR7600000000000000000001001",
        name="Compte G1 Vide",
    )
    db_session.add_all([access, ba])
    db_session.commit()

    r = client.get(f"/api/treasury/daily-balance?entity_id={entity.id}&days=90")
    assert r.status_code == 200
    body = r.json()
    assert body["entity_id"] == entity.id
    assert body["points"] == []
    assert body["latest_balance"] is None
    assert body["latest_date"] is None


# ---------------------------------------------------------------------------
# Cas 2 : entité avec imports → 90 points triés par date croissante
# ---------------------------------------------------------------------------

def test_daily_balance_normal_period(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """Entité avec un import récent → 90 points triés chronologiquement."""
    entity = Entity(name="G1 Normal Entity", legal_name="G1 Normal Entity")
    db_session.add(entity)
    db_session.flush()
    access = UserEntityAccess(user_id=auth_user.id, entity_id=entity.id)
    ba = BankAccount(
        entity_id=entity.id,
        bank_code="qonto",
        bank_name="Qonto",
        iban="FR7600000000000000000001002",
        name="Compte G1 Normal",
    )
    db_session.add_all([access, ba])
    db_session.flush()

    today = date.today()
    ir = _mk_import(
        db_session,
        bank_account=ba,
        closing=Decimal("5000.00"),
        period_end=today,
    )
    # Quelques transactions dans la période
    _mk_tx(db_session, bank_account=ba, import_record=ir,
           op_date=today - timedelta(days=5), amount=Decimal("1000"), row_idx=1)
    _mk_tx(db_session, bank_account=ba, import_record=ir,
           op_date=today - timedelta(days=2), amount=Decimal("-300"), row_idx=2)
    db_session.commit()

    r = client.get(f"/api/treasury/daily-balance?entity_id={entity.id}&days=90")
    assert r.status_code == 200
    body = r.json()
    assert body["entity_id"] == entity.id
    assert body["days"] == 90
    points = body["points"]
    assert len(points) == 90

    # Vérifier que les points sont triés par date croissante
    dates = [p["date"] for p in points]
    assert dates == sorted(dates)

    # Le dernier point doit avoir une balance non nulle
    assert body["latest_balance"] is not None
    assert float(body["latest_balance"]) == pytest.approx(5000.00)


# ---------------------------------------------------------------------------
# Cas 3 : accès refusé si entité étrangère → 403 (user READER)
# ---------------------------------------------------------------------------

def test_daily_balance_access_denied_foreign_entity(
    client: TestClient,
    auth_user_reader: User,
    db_session: Session,
) -> None:
    """Entité non accessible au user READER → 403."""
    other_entity = Entity(name="G1 Autre Entité", legal_name="G1 Autre Entité")
    db_session.add(other_entity)
    db_session.commit()

    r = client.get(f"/api/treasury/daily-balance?entity_id={other_entity.id}")
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Cas 4 : authentification requise
# ---------------------------------------------------------------------------

def test_daily_balance_requires_auth(client: TestClient) -> None:
    r = client.get("/api/treasury/daily-balance?entity_id=1")
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Cas 5 : paramètre days personnalisé (30j)
# ---------------------------------------------------------------------------

def test_daily_balance_custom_days(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """days=30 → exactement 30 points."""
    entity = Entity(name="G1 Days30 Entity", legal_name="G1 Days30 Entity")
    db_session.add(entity)
    db_session.flush()
    access = UserEntityAccess(user_id=auth_user.id, entity_id=entity.id)
    ba = BankAccount(
        entity_id=entity.id,
        bank_code="delubac",
        bank_name="Delubac",
        iban="FR7600000000000000000001003",
        name="Compte G1 Days30",
    )
    db_session.add_all([access, ba])
    db_session.flush()

    today = date.today()
    _mk_import(
        db_session,
        bank_account=ba,
        closing=Decimal("2000.00"),
        period_end=today,
    )
    db_session.commit()

    r = client.get(f"/api/treasury/daily-balance?entity_id={entity.id}&days=30")
    assert r.status_code == 200
    body = r.json()
    assert len(body["points"]) == 30
