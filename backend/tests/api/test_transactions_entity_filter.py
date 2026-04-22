"""GET /api/transactions?entity_id=... — filtre par entité.

Phase A / Plan 5a : on peut restreindre la liste des transactions à
une entité particulière parmi celles auxquelles l'utilisateur a accès.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.entity import Entity
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction
from app.models.user import User
from app.models.user_entity_access import UserEntityAccess


def _make_tx(
    session: Session,
    *,
    bank_account: BankAccount,
    import_id: int,
    label: str,
    amount: Decimal,
    op_date: date,
    row: int,
) -> Transaction:
    tx = Transaction(
        bank_account_id=bank_account.id,
        import_id=import_id,
        operation_date=op_date,
        value_date=op_date,
        amount=amount,
        label=label,
        raw_label=label,
        dedup_key=f"dk-{bank_account.id}-{row}-{label}",
        statement_row_index=row,
    )
    session.add(tx)
    session.flush()
    return tx


def _seed_entity_with_tx(
    session: Session,
    *,
    user: User,
    entity_name: str,
    iban: str,
    tx_label: str,
) -> tuple[Entity, BankAccount, Transaction]:
    e = Entity(name=entity_name, legal_name=entity_name)
    session.add(e)
    session.flush()
    session.add(UserEntityAccess(user_id=user.id, entity_id=e.id))
    ba = BankAccount(
        entity_id=e.id, bank_code="delubac", bank_name="Delubac",
        iban=iban, name=f"Compte {entity_name}",
    )
    session.add(ba)
    session.flush()
    imp = ImportRecord(
        bank_account_id=ba.id, bank_code="delubac",
        status=ImportStatus.COMPLETED, filename="seed.pdf",
    )
    session.add(imp)
    session.flush()
    tx = _make_tx(
        session, bank_account=ba, import_id=imp.id,
        label=tx_label, amount=Decimal("100.00"),
        op_date=date(2026, 1, 15), row=1,
    )
    session.commit()
    return e, ba, tx


def test_transactions_filter_by_entity_id(
    client: TestClient, db_session: Session, auth_user_admin: User,
) -> None:
    e1, _ba1, _tx1 = _seed_entity_with_tx(
        db_session, user=auth_user_admin,
        entity_name="SAS Alpha", iban="FR7600000000000000000000111",
        tx_label="TX-ALPHA",
    )
    e2, _ba2, _tx2 = _seed_entity_with_tx(
        db_session, user=auth_user_admin,
        entity_name="SAS Beta", iban="FR7600000000000000000000222",
        tx_label="TX-BETA",
    )

    # Sans filtre : 2 transactions (une par entité)
    resp_all = client.get("/api/transactions", params={"per_page": 100})
    assert resp_all.status_code == 200
    assert resp_all.json()["total"] == 2

    # Avec filtre entity_id=e1.id : seulement la tx de e1
    resp = client.get(
        "/api/transactions",
        params={"entity_id": e1.id, "per_page": 100},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["label"] == "TX-ALPHA"

    # Et dans l'autre sens
    resp2 = client.get(
        "/api/transactions",
        params={"entity_id": e2.id, "per_page": 100},
    )
    assert resp2.status_code == 200
    assert resp2.json()["items"][0]["label"] == "TX-BETA"


def test_transactions_entity_id_without_access_is_forbidden(
    client: TestClient, db_session: Session, auth_user_reader: User,
) -> None:
    # Entity à laquelle le reader n'a PAS accès
    e_other = Entity(name="SAS Interdite", legal_name="SAS Interdite")
    db_session.add(e_other)
    db_session.commit()

    resp = client.get(
        "/api/transactions",
        params={"entity_id": e_other.id},
    )
    assert resp.status_code == 403
