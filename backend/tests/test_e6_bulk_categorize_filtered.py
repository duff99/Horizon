"""E6 — POST /api/transactions/bulk-categorize-filtered catégorise via filtres."""
import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.category import Category
from app.models.entity import Entity
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction, TransactionCategorizationSource
from app.models.user import User, UserRole
from app.models.user_entity_access import UserEntityAccess
from app.security import hash_password


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unique() -> str:
    return uuid.uuid4().hex


def _create_entity(db_session: Session, name: str | None = None) -> Entity:
    n = name or f"Entité E6 {_unique()}"
    e = Entity(name=n, legal_name=n)
    db_session.add(e)
    db_session.flush()
    return e


def _create_bank_account(db_session: Session, entity_id: int) -> BankAccount:
    ba = BankAccount(
        entity_id=entity_id,
        bank_code="delubac",
        bank_name="Delubac",
        iban=f"FR76000{_unique()[:20]}",
        name=f"Compte E6 {_unique()}",
    )
    db_session.add(ba)
    db_session.flush()
    return ba


def _create_import(db_session: Session, bank_account_id: int) -> ImportRecord:
    imp = ImportRecord(
        bank_account_id=bank_account_id,
        filename="test.pdf",
        file_sha256=_unique() * 2,
        bank_code="delubac",
        status=ImportStatus.COMPLETED,
    )
    db_session.add(imp)
    db_session.flush()
    return imp


def _create_transaction(
    db_session: Session,
    bank_account_id: int,
    import_id: int,
    label: str = "TX",
    categorized_by: TransactionCategorizationSource = TransactionCategorizationSource.NONE,
    amount: Decimal = Decimal("-100.00"),
) -> Transaction:
    key = _unique()
    tx = Transaction(
        bank_account_id=bank_account_id,
        import_id=import_id,
        operation_date=date(2026, 1, 15),
        value_date=date(2026, 1, 15),
        amount=amount,
        label=label,
        raw_label=label,
        normalized_label=label.upper(),
        dedup_key=key[:64],
        statement_row_index=0,
        categorized_by=categorized_by,
    )
    db_session.add(tx)
    db_session.flush()
    return tx


def _create_category(db_session: Session, name: str = "Test Cat") -> Category:
    cat = Category(name=f"{name} {_unique()}", slug=_unique())
    db_session.add(cat)
    db_session.flush()
    return cat


def _login_admin(client, db_session: Session, entity_id: int | None = None) -> User:
    u = User(
        email=f"{_unique()}@test.com",
        password_hash=hash_password("test-password-123"),
        role=UserRole.ADMIN,
    )
    db_session.add(u)
    db_session.flush()
    if entity_id is not None:
        db_session.add(UserEntityAccess(user_id=u.id, entity_id=entity_id))
        db_session.flush()
    db_session.commit()
    resp = client.post("/api/auth/login", json={"email": u.email, "password": "test-password-123"})
    assert resp.status_code == 200
    return u


def _login_reader(client, db_session: Session) -> User:
    u = User(
        email=f"{_unique()}@test.com",
        password_hash=hash_password("test-password-123"),
        role=UserRole.READER,
    )
    db_session.add(u)
    db_session.flush()
    db_session.commit()
    resp = client.post("/api/auth/login", json={"email": u.email, "password": "test-password-123"})
    assert resp.status_code == 200
    return u


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_bulk_categorize_filtered_uncategorized(client, db_session):
    entity = _create_entity(db_session)
    ba = _create_bank_account(db_session, entity.id)
    imp = _create_import(db_session, ba.id)
    cat = _create_category(db_session, "Charges test")
    tx1 = _create_transaction(db_session, ba.id, imp.id, label="PRLV TEST", categorized_by=TransactionCategorizationSource.NONE)
    tx2 = _create_transaction(db_session, ba.id, imp.id, label="PRLV TEST 2", categorized_by=TransactionCategorizationSource.NONE)
    tx3 = _create_transaction(db_session, ba.id, imp.id, label="AUTRE", categorized_by=TransactionCategorizationSource.MANUAL)
    db_session.commit()

    _login_admin(client, db_session, entity_id=entity.id)

    resp = client.post(
        "/api/transactions/bulk-categorize-filtered",
        json={
            "category_id": cat.id,
            "entity_id": entity.id,
            "uncategorized": True,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["updated_count"] == 2  # tx1 + tx2, pas tx3

    db_session.refresh(tx1)
    db_session.refresh(tx3)
    assert tx1.category_id == cat.id
    assert tx3.category_id != cat.id  # tx3 non modifiée


def test_bulk_categorize_filtered_reader_forbidden(client, db_session):
    _login_reader(client, db_session)
    resp = client.post(
        "/api/transactions/bulk-categorize-filtered",
        json={"category_id": 1},
    )
    assert resp.status_code == 403


def test_bulk_categorize_filtered_all_transactions(client, db_session):
    """Sans filtre uncategorized — catégorise toutes les transactions de l'entité."""
    entity = _create_entity(db_session)
    ba = _create_bank_account(db_session, entity.id)
    imp = _create_import(db_session, ba.id)
    cat = _create_category(db_session, "Charges all")
    tx1 = _create_transaction(db_session, ba.id, imp.id, label="TX A")
    tx2 = _create_transaction(db_session, ba.id, imp.id, label="TX B")
    db_session.commit()

    _login_admin(client, db_session, entity_id=entity.id)

    resp = client.post(
        "/api/transactions/bulk-categorize-filtered",
        json={
            "category_id": cat.id,
            "entity_id": entity.id,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["updated_count"] >= 2

    db_session.refresh(tx1)
    db_session.refresh(tx2)
    assert tx1.category_id == cat.id
    assert tx2.category_id == cat.id


def test_bulk_categorize_filtered_amount_filter(client, db_session):
    """Filtre amount_min s'applique correctement."""
    entity = _create_entity(db_session)
    ba = _create_bank_account(db_session, entity.id)
    imp = _create_import(db_session, ba.id)
    cat = _create_category(db_session, "Gros debit")
    tx_small = _create_transaction(db_session, ba.id, imp.id, label="SMALL", amount=Decimal("-10.00"))
    tx_large = _create_transaction(db_session, ba.id, imp.id, label="LARGE", amount=Decimal("-500.00"))
    db_session.commit()

    _login_admin(client, db_session, entity_id=entity.id)

    resp = client.post(
        "/api/transactions/bulk-categorize-filtered",
        json={
            "category_id": cat.id,
            "entity_id": entity.id,
            "amount_min": "100",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["updated_count"] == 1

    db_session.refresh(tx_small)
    db_session.refresh(tx_large)
    assert tx_large.category_id == cat.id
    assert tx_small.category_id != cat.id
