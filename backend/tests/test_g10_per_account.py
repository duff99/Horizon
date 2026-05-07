"""Tests pour GET /api/treasury/per-account (G10)."""
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


# ---------------------------------------------------------------------------
# Cas 1 : un seul compte → 1 PerAccountBalance avec sparkline 30 points
# ---------------------------------------------------------------------------

def test_per_account_single_account(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """Un seul compte bancaire → 1 PerAccountBalance, sparkline de 30 points."""
    entity = Entity(name="G10 Single Entity", legal_name="G10 Single Entity")
    db_session.add(entity)
    db_session.flush()
    access = UserEntityAccess(user_id=auth_user.id, entity_id=entity.id)
    ba = BankAccount(
        entity_id=entity.id,
        bank_code="delubac",
        bank_name="Delubac",
        iban="FR7600000000000000000002001",
        name="Compte G10 Unique",
    )
    db_session.add_all([access, ba])
    db_session.flush()

    today = date.today()
    _mk_import(
        db_session,
        bank_account=ba,
        closing=Decimal("8500.00"),
        period_end=today,
    )
    db_session.commit()

    r = client.get(f"/api/treasury/per-account?entity_id={entity.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["entity_id"] == entity.id
    accounts = body["accounts"]
    assert len(accounts) == 1

    acc = accounts[0]
    assert acc["account_id"] == ba.id
    assert acc["account_name"] == "Compte G10 Unique"
    assert acc["bank_name"] == "Delubac"
    assert acc["iban_last4"] == "2001"
    assert acc["balance_cents"] == 850000  # 8500.00 * 100
    assert len(acc["sparkline"]) == 30


# ---------------------------------------------------------------------------
# Cas 2 : variation_30d calculée si import ancien disponible
# ---------------------------------------------------------------------------

def test_per_account_variation_30d(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """Deux imports (actuel + ancien > 30j) → variation_30d_cents calculée."""
    entity = Entity(name="G10 Variation Entity", legal_name="G10 Variation Entity")
    db_session.add(entity)
    db_session.flush()
    access = UserEntityAccess(user_id=auth_user.id, entity_id=entity.id)
    ba = BankAccount(
        entity_id=entity.id,
        bank_code="qonto",
        bank_name="Qonto",
        iban="FR7600000000000000000002002",
        name="Compte G10 Variation",
    )
    db_session.add_all([access, ba])
    db_session.flush()

    today = date.today()
    # Import courant
    _mk_import(db_session, bank_account=ba, closing=Decimal("10000.00"), period_end=today)
    # Import vieux (il y a 45 jours)
    old_date = today - timedelta(days=45)
    _mk_import(db_session, bank_account=ba, closing=Decimal("7000.00"), period_end=old_date)
    db_session.commit()

    r = client.get(f"/api/treasury/per-account?entity_id={entity.id}")
    assert r.status_code == 200
    acc = r.json()["accounts"][0]

    assert acc["balance_cents"] == 1_000_000  # 10000 * 100
    assert acc["balance_30d_ago_cents"] == 700_000  # 7000 * 100
    assert acc["variation_30d_cents"] == 300_000  # 10000 - 7000 = 3000€ → 300000 cts


# ---------------------------------------------------------------------------
# Cas 3 : accès refusé pour entité étrangère → 403 (user READER)
# ---------------------------------------------------------------------------

def test_per_account_access_denied(
    client: TestClient,
    auth_user_reader: User,
    db_session: Session,
) -> None:
    """Entité non accessible au user READER → 403."""
    other_entity = Entity(name="G10 Autre Entité", legal_name="G10 Autre Entité")
    db_session.add(other_entity)
    db_session.commit()

    r = client.get(f"/api/treasury/per-account?entity_id={other_entity.id}")
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Cas 4 : authentification requise
# ---------------------------------------------------------------------------

def test_per_account_requires_auth(client: TestClient) -> None:
    r = client.get("/api/treasury/per-account?entity_id=1")
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Cas 5 : entité sans compte → liste vide
# ---------------------------------------------------------------------------

def test_per_account_empty_entity(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """Entité sans aucun compte bancaire → accounts=[]."""
    entity = Entity(name="G10 Empty Entity", legal_name="G10 Empty Entity")
    db_session.add(entity)
    db_session.flush()
    access = UserEntityAccess(user_id=auth_user.id, entity_id=entity.id)
    db_session.add(access)
    db_session.commit()

    r = client.get(f"/api/treasury/per-account?entity_id={entity.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["accounts"] == []


# ---------------------------------------------------------------------------
# Cas 6 : multi-comptes — wrapping géré (5+ comptes)
# ---------------------------------------------------------------------------

def test_per_account_multiple_accounts(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """5 comptes pour une entité → 5 PerAccountBalance retournés."""
    entity = Entity(name="G10 Multi Entity", legal_name="G10 Multi Entity")
    db_session.add(entity)
    db_session.flush()
    access = UserEntityAccess(user_id=auth_user.id, entity_id=entity.id)
    db_session.add(access)
    db_session.flush()

    today = date.today()
    for i in range(5):
        ba = BankAccount(
            entity_id=entity.id,
            bank_code="delubac",
            bank_name="Delubac",
            iban=f"FR760000000000000000000{3000 + i}",
            name=f"Compte G10 Multi {i}",
        )
        db_session.add(ba)
        db_session.flush()
        _mk_import(db_session, bank_account=ba, closing=Decimal(f"{1000 * (i+1)}.00"), period_end=today)

    db_session.commit()

    r = client.get(f"/api/treasury/per-account?entity_id={entity.id}")
    assert r.status_code == 200
    body = r.json()
    assert len(body["accounts"]) == 5
