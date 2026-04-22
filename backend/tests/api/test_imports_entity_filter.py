"""GET /api/imports?entity_id=... — filtre par entité."""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.entity import Entity
from app.models.import_record import ImportRecord, ImportStatus
from app.models.user import User
from app.models.user_entity_access import UserEntityAccess


def _seed_entity_with_import(
    session: Session, *, user: User, entity_name: str, iban: str, filename: str,
) -> tuple[Entity, BankAccount, ImportRecord]:
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
        status=ImportStatus.COMPLETED, filename=filename,
    )
    session.add(imp)
    session.commit()
    session.refresh(imp)
    return e, ba, imp


def test_imports_filter_by_entity_id(
    client: TestClient, db_session: Session, auth_user_admin: User,
) -> None:
    e1, _ba1, imp1 = _seed_entity_with_import(
        db_session, user=auth_user_admin,
        entity_name="SAS Alpha", iban="FR7600000000000000000000111",
        filename="alpha.pdf",
    )
    e2, _ba2, imp2 = _seed_entity_with_import(
        db_session, user=auth_user_admin,
        entity_name="SAS Beta", iban="FR7600000000000000000000222",
        filename="beta.pdf",
    )

    # Sans filtre : 2 imports
    resp_all = client.get("/api/imports")
    assert resp_all.status_code == 200
    assert len(resp_all.json()) == 2

    # Avec filtre entity_id=e1.id
    resp = client.get("/api/imports", params={"entity_id": e1.id})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["id"] == imp1.id
    assert body[0]["filename"] == "alpha.pdf"

    resp2 = client.get("/api/imports", params={"entity_id": e2.id})
    assert resp2.status_code == 200
    assert resp2.json()[0]["id"] == imp2.id


def test_imports_entity_id_without_access_is_forbidden(
    client: TestClient, db_session: Session, auth_user_reader: User,
) -> None:
    e_other = Entity(name="SAS Interdite", legal_name="SAS Interdite")
    db_session.add(e_other)
    db_session.commit()

    resp = client.get("/api/imports", params={"entity_id": e_other.id})
    assert resp.status_code == 403
