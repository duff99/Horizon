"""Tests de permissions sur GET /api/bank-accounts pour les users READER.

Couvre :
- Un READER ne voit que les comptes bancaires des entités auxquelles il a accès.
- Un READER ne peut pas créer un compte bancaire (403).
- Un ADMIN voit tous les comptes bancaires.
"""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.entity import Entity
from app.models.user_entity_access import UserEntityAccess


def test_reader_can_list_only_accessible_bank_accounts(
    client: TestClient, auth_user_reader, db_session: Session
) -> None:
    """Un READER n'obtient que les comptes bancaires de ses entités accessibles."""
    entity_a = Entity(name="Entite Reader A", legal_name="Entite Reader A SAS")
    entity_b = Entity(name="Entite Reader B", legal_name="Entite Reader B SAS")
    db_session.add_all([entity_a, entity_b])
    db_session.flush()

    # Accès uniquement à entity_a
    access = UserEntityAccess(user_id=auth_user_reader.id, entity_id=entity_a.id)
    db_session.add(access)

    ba_a = BankAccount(
        entity_id=entity_a.id,
        bank_code="delubac",
        bank_name="Delubac",
        iban="FR7611111111111111111111111",
        name="Compte A accessible",
    )
    ba_b = BankAccount(
        entity_id=entity_b.id,
        bank_code="delubac",
        bank_name="Delubac",
        iban="FR7622222222222222222222222",
        name="Compte B inaccessible",
    )
    db_session.add_all([ba_a, ba_b])
    db_session.commit()
    db_session.refresh(ba_a)
    db_session.refresh(ba_b)

    resp = client.get("/api/bank-accounts")
    assert resp.status_code == 200, resp.text
    ids = [item["id"] for item in resp.json()]
    assert ba_a.id in ids, "Le compte A accessible doit etre retourne"
    assert ba_b.id not in ids, "Le compte B inaccessible ne doit pas etre retourne"


def test_reader_cannot_create_bank_account(
    client: TestClient, auth_user_reader, db_session: Session
) -> None:
    """Un READER recoit 403 en tentant de creer un compte bancaire."""
    entity = Entity(name="Entite Reader C", legal_name="Entite Reader C SAS")
    db_session.add(entity)
    db_session.commit()

    resp = client.post("/api/bank-accounts", json={
        "entity_id": entity.id,
        "bank_code": "delubac",
        "bank_name": "Delubac",
        "iban": "FR7633333333333333333333333",
        "name": "Tentative creation READER",
    })
    assert resp.status_code == 403, resp.text


def test_admin_lists_all_bank_accounts(
    client: TestClient, auth_user, db_session: Session
) -> None:
    """Un ADMIN voit tous les comptes bancaires, quelle que soit l'entite."""
    entity_x = Entity(name="Entite Admin X", legal_name="Entite Admin X SAS")
    entity_y = Entity(name="Entite Admin Y", legal_name="Entite Admin Y SAS")
    db_session.add_all([entity_x, entity_y])
    db_session.flush()

    ba_x = BankAccount(
        entity_id=entity_x.id,
        bank_code="delubac",
        bank_name="Delubac",
        iban="FR7644444444444444444444444",
        name="Compte Admin X",
    )
    ba_y = BankAccount(
        entity_id=entity_y.id,
        bank_code="delubac",
        bank_name="Delubac",
        iban="FR7655555555555555555555555",
        name="Compte Admin Y",
    )
    db_session.add_all([ba_x, ba_y])
    db_session.commit()
    db_session.refresh(ba_x)
    db_session.refresh(ba_y)

    resp = client.get("/api/bank-accounts")
    assert resp.status_code == 200, resp.text
    ids = [item["id"] for item in resp.json()]
    assert ba_x.id in ids, "Le compte X doit etre visible par l'admin"
    assert ba_y.id in ids, "Le compte Y doit etre visible par l'admin"
