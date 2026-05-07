"""TDD C6 — Leak quantitatif cross-tenant dans preview_rule.

Pour une règle GLOBALE (entity_id IS NULL), le comptage de transactions
doit être restreint aux entités accessibles par l'utilisateur appelant.
Sans ce filtre, un READER voyait le décompte sur TOUTES les entités,
y compris celles auxquelles il n'a pas accès.
"""
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.entity import Entity
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction, TransactionCategorizationSource
from app.models.user import User, UserRole
from app.models.user_entity_access import UserEntityAccess
from app.security import hash_password


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_import(db_session: Session, bank_account_id: int, suffix: str) -> ImportRecord:
    imp = ImportRecord(
        bank_account_id=bank_account_id,
        filename=f"import_{suffix}.pdf",
        file_sha256=f"c6{suffix}"[:64].ljust(64, "0"),
        bank_code="DELUBAC",
        status=ImportStatus.COMPLETED,
    )
    db_session.add(imp)
    db_session.flush()
    return imp


def _make_tx(
    db_session: Session,
    bank_account_id: int,
    import_id: int,
    *,
    normalized_label: str,
    amount: Decimal,
    row_idx: int,
) -> Transaction:
    tx = Transaction(
        bank_account_id=bank_account_id,
        import_id=import_id,
        operation_date=date(2026, 2, 1),
        value_date=date(2026, 2, 1),
        amount=amount,
        label=normalized_label,
        raw_label=normalized_label,
        normalized_label=normalized_label,
        dedup_key=f"c6-{bank_account_id}-{row_idx}-" + "x" * 40,
        statement_row_index=row_idx,
        is_aggregation_parent=False,
        parent_transaction_id=None,
        categorized_by=TransactionCategorizationSource.NONE,
    )
    db_session.add(tx)
    db_session.flush()
    return tx


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def seed_two_entities(db_session: Session):
    """Crée E1 (5 tx LOYER X) et E2 (2 tx LOYER Y). Retourne (e1, e2, ba1, ba2)."""
    e1 = Entity(name="Entité C6-E1", legal_name="Entité C6-E1")
    e2 = Entity(name="Entité C6-E2", legal_name="Entité C6-E2")
    db_session.add_all([e1, e2])
    db_session.flush()

    ba1 = BankAccount(
        entity_id=e1.id,
        bank_code="delubac",
        bank_name="Delubac",
        iban="FR7600000000000000000001001",
        name="Compte E1",
    )
    ba2 = BankAccount(
        entity_id=e2.id,
        bank_code="delubac",
        bank_name="Delubac",
        iban="FR7600000000000000000002001",
        name="Compte E2",
    )
    db_session.add_all([ba1, ba2])
    db_session.flush()

    imp1 = _make_import(db_session, ba1.id, "e1")
    imp2 = _make_import(db_session, ba2.id, "e2")

    for i in range(5):
        _make_tx(
            db_session, ba1.id, imp1.id,
            normalized_label="LOYER X",
            amount=Decimal("-1000.00"),
            row_idx=100 + i,
        )
    for i in range(2):
        _make_tx(
            db_session, ba2.id, imp2.id,
            normalized_label="LOYER Y",
            amount=Decimal("-500.00"),
            row_idx=200 + i,
        )

    db_session.commit()
    return e1, e2, ba1, ba2


@pytest.fixture()
def reader_client(client: TestClient, db_session: Session, seed_two_entities):
    """READER authentifié avec accès uniquement à E2."""
    _e1, e2, _ba1, _ba2 = seed_two_entities

    user = User(
        email="reader_c6@example.com",
        password_hash=hash_password("test-password-123"),
        role=UserRole.READER,
    )
    db_session.add(user)
    db_session.flush()

    access = UserEntityAccess(user_id=user.id, entity_id=e2.id)
    db_session.add(access)
    db_session.commit()

    resp = client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "test-password-123"},
    )
    assert resp.status_code == 200, f"Login reader échoué : {resp.text}"
    return client


@pytest.fixture()
def admin_client(client: TestClient, db_session: Session, seed_two_entities):
    """ADMIN authentifié (accès à toutes les entités)."""
    user = User(
        email="admin_c6@example.com",
        password_hash=hash_password("test-password-123"),
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    db_session.commit()

    resp = client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "test-password-123"},
    )
    assert resp.status_code == 200, f"Login admin échoué : {resp.text}"
    return client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

_GLOBAL_RULE_PAYLOAD = {
    "name": "Test LOYER global",
    "entity_id": None,
    "priority": 10,
    "label_operator": "CONTAINS",
    "label_value": "LOYER",
    "direction": "ANY",
    "amount_operator": None,
    "amount_value": None,
    "amount_value2": None,
    "counterparty_id": None,
    "bank_account_id": None,
    "category_id": 1,
}


def test_reader_preview_global_rule_sees_only_accessible_entities(
    reader_client: TestClient,
) -> None:
    """Un READER avec accès à E2 seulement doit voir 2 transactions (LOYER Y × 2),
    et non 7 (qui incluraient les 5 LOYER X de E1 auxquelles il n'a pas accès).
    """
    resp = reader_client.post("/api/rules/preview", json=_GLOBAL_RULE_PAYLOAD)
    assert resp.status_code == 200, f"Preview échoué : {resp.text}"
    data = resp.json()
    assert data["matching_count"] == 2, (
        f"READER devrait voir 2 transactions (E2 uniquement), "
        f"pas {data['matching_count']} (leak cross-tenant détecté)"
    )


def test_admin_preview_global_rule_sees_all_entities(
    admin_client: TestClient,
) -> None:
    """Un ADMIN doit voir toutes les transactions matchant la règle (7 au total)."""
    resp = admin_client.post("/api/rules/preview", json=_GLOBAL_RULE_PAYLOAD)
    assert resp.status_code == 200, f"Preview admin échoué : {resp.text}"
    data = resp.json()
    assert data["matching_count"] == 7, (
        f"ADMIN devrait voir 7 transactions (E1+E2), "
        f"pas {data['matching_count']}"
    )
