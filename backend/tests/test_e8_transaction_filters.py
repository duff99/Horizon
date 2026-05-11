"""E7/E8 — Tests des nouveaux filtres transactions : SEPA enfants, amount_min/max."""
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


def _create_entity(db_session: Session) -> Entity:
    e = Entity(name=f"Entité E8 {_unique()}", legal_name=f"Entité E8 {_unique()}")
    db_session.add(e)
    db_session.flush()
    return e


def _create_bank_account(db_session: Session, entity_id: int) -> BankAccount:
    ba = BankAccount(
        entity_id=entity_id,
        bank_code="delubac",
        bank_name="Delubac",
        iban=f"FR76000{_unique()[:20]}",
        name=f"Compte E8 {_unique()}",
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
    amount: Decimal,
    parent_id: int | None = None,
) -> Transaction:
    key = _unique()
    tx = Transaction(
        bank_account_id=bank_account_id,
        import_id=import_id,
        operation_date=date(2026, 1, 15),
        value_date=date(2026, 1, 15),
        amount=amount,
        label=f"TX {key}",
        raw_label=f"TX {key}",
        normalized_label=f"TX {key}",
        dedup_key=key[:64],
        statement_row_index=0,
        parent_transaction_id=parent_id,
    )
    db_session.add(tx)
    db_session.flush()
    return tx


def _login_user(client, email: str, password: str = "test-password-123") -> None:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200


def _setup_user_with_access(db_session: Session, entity_id: int, role=UserRole.ADMIN) -> User:
    u = User(
        email=f"{_unique()}@test.com",
        password_hash=hash_password("test-password-123"),
        role=role,
    )
    db_session.add(u)
    db_session.flush()
    access = UserEntityAccess(user_id=u.id, entity_id=entity_id)
    db_session.add(access)
    db_session.flush()
    return u


# ---------------------------------------------------------------------------
# Tests E8 — amount_min / amount_max
# ---------------------------------------------------------------------------

def test_amount_min_filter(client, db_session):
    entity = _create_entity(db_session)
    ba = _create_bank_account(db_session, entity.id)
    imp = _create_import(db_session, ba.id)
    user = _setup_user_with_access(db_session, entity.id)
    db_session.commit()

    tx_small = _create_transaction(db_session, ba.id, imp.id, Decimal("-10.00"))
    tx_large = _create_transaction(db_session, ba.id, imp.id, Decimal("-500.00"))
    db_session.commit()

    _login_user(client, user.email)

    resp = client.get(f"/api/transactions?entity_id={entity.id}&amount_min=100")
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["items"]]
    assert tx_large.id in ids
    assert tx_small.id not in ids


def test_amount_max_filter(client, db_session):
    entity = _create_entity(db_session)
    ba = _create_bank_account(db_session, entity.id)
    imp = _create_import(db_session, ba.id)
    user = _setup_user_with_access(db_session, entity.id)
    db_session.commit()

    tx_small = _create_transaction(db_session, ba.id, imp.id, Decimal("-10.00"))
    tx_large = _create_transaction(db_session, ba.id, imp.id, Decimal("-500.00"))
    db_session.commit()

    _login_user(client, user.email)

    resp = client.get(f"/api/transactions?entity_id={entity.id}&amount_max=50")
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["items"]]
    assert tx_small.id in ids
    assert tx_large.id not in ids


def test_amount_min_max_combined(client, db_session):
    entity = _create_entity(db_session)
    ba = _create_bank_account(db_session, entity.id)
    imp = _create_import(db_session, ba.id)
    user = _setup_user_with_access(db_session, entity.id)
    db_session.commit()

    tx_small = _create_transaction(db_session, ba.id, imp.id, Decimal("-5.00"))
    tx_mid = _create_transaction(db_session, ba.id, imp.id, Decimal("-100.00"))
    tx_large = _create_transaction(db_session, ba.id, imp.id, Decimal("-1000.00"))
    db_session.commit()

    _login_user(client, user.email)

    resp = client.get(f"/api/transactions?entity_id={entity.id}&amount_min=50&amount_max=500")
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["items"]]
    assert tx_mid.id in ids
    assert tx_small.id not in ids
    assert tx_large.id not in ids


def test_amount_filter_absolute_value_positive_tx(client, db_session):
    """amount_min/max s'applique en valeur absolue — les transactions positives (crédit) doivent aussi matcher."""
    entity = _create_entity(db_session)
    ba = _create_bank_account(db_session, entity.id)
    imp = _create_import(db_session, ba.id)
    user = _setup_user_with_access(db_session, entity.id)
    db_session.commit()

    tx_credit = _create_transaction(db_session, ba.id, imp.id, Decimal("300.00"))
    db_session.commit()

    _login_user(client, user.email)

    resp = client.get(f"/api/transactions?entity_id={entity.id}&amount_min=200")
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["items"]]
    assert tx_credit.id in ids


# ---------------------------------------------------------------------------
# Tests E7 — include_sepa_children
# ---------------------------------------------------------------------------

def test_sepa_children_hidden_by_default(client, db_session):
    entity = _create_entity(db_session)
    ba = _create_bank_account(db_session, entity.id)
    imp = _create_import(db_session, ba.id)
    user = _setup_user_with_access(db_session, entity.id)
    db_session.commit()

    parent_tx = _create_transaction(db_session, ba.id, imp.id, Decimal("-100.00"))
    db_session.commit()
    child_tx = _create_transaction(db_session, ba.id, imp.id, Decimal("-50.00"), parent_id=parent_tx.id)
    db_session.commit()

    _login_user(client, user.email)

    resp = client.get(f"/api/transactions?entity_id={entity.id}")
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["items"]]
    assert child_tx.id not in ids


def test_sepa_children_visible_when_toggled(client, db_session):
    entity = _create_entity(db_session)
    ba = _create_bank_account(db_session, entity.id)
    imp = _create_import(db_session, ba.id)
    user = _setup_user_with_access(db_session, entity.id)
    db_session.commit()

    parent_tx = _create_transaction(db_session, ba.id, imp.id, Decimal("-100.00"))
    db_session.commit()
    child_tx = _create_transaction(db_session, ba.id, imp.id, Decimal("-50.00"), parent_id=parent_tx.id)
    db_session.commit()

    _login_user(client, user.email)

    resp = client.get(f"/api/transactions?entity_id={entity.id}&include_sepa_children=true")
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["items"]]
    assert child_tx.id in ids


def test_counterparty_filter_includes_sepa_children_implicitly(client, db_session):
    """Regression : filtrer par counterparty_id doit inclure les enfants SEPA.

    Cas observé en prod : un tier (ACRONOS, NIZAR MOUADDEB...) dont toutes
    les transactions sont des enfants SEPA. Sans cette exception, la page
    /transactions?counterparty=X renvoyait toujours 0 ligne car les enfants
    SEPA étaient masqués par défaut et les batch parents n'ont pas de tier.
    """
    from app.models.counterparty import Counterparty

    entity = _create_entity(db_session)
    ba = _create_bank_account(db_session, entity.id)
    imp = _create_import(db_session, ba.id)
    user = _setup_user_with_access(db_session, entity.id)
    cp = Counterparty(entity_id=entity.id, name=f"Tiers {_unique()}", normalized_name="tiers")
    db_session.add(cp)
    db_session.flush()
    db_session.commit()

    parent_tx = _create_transaction(db_session, ba.id, imp.id, Decimal("-1000.00"))
    db_session.commit()
    child_tx = _create_transaction(
        db_session, ba.id, imp.id, Decimal("-250.00"), parent_id=parent_tx.id,
    )
    child_tx.counterparty_id = cp.id
    db_session.commit()

    _login_user(client, user.email)

    # Sans counterparty_id : enfant SEPA masqué (comportement E7 inchangé)
    resp = client.get(f"/api/transactions?entity_id={entity.id}")
    assert resp.status_code == 200
    assert child_tx.id not in [i["id"] for i in resp.json()["items"]]

    # Avec counterparty_id : enfant SEPA exposé même sans toggle SEPA
    resp = client.get(
        f"/api/transactions?entity_id={entity.id}&counterparty_id={cp.id}",
    )
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["items"]]
    assert child_tx.id in ids, (
        "Le filtre counterparty doit afficher tous les tx du tiers, "
        "y compris les enfants SEPA"
    )
