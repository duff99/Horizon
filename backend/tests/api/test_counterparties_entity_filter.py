"""GET /api/counterparties?entity_id=... — filtre par entité."""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.counterparty import Counterparty, CounterpartyStatus
from app.models.entity import Entity
from app.models.user import User
from app.models.user_entity_access import UserEntityAccess


def _seed_entity_with_counterparty(
    session: Session, *, user: User, entity_name: str, cp_name: str,
) -> tuple[Entity, Counterparty]:
    e = Entity(name=entity_name, legal_name=entity_name)
    session.add(e)
    session.flush()
    session.add(UserEntityAccess(user_id=user.id, entity_id=e.id))
    cp = Counterparty(
        entity_id=e.id, name=cp_name, normalized_name=cp_name.lower(),
        status=CounterpartyStatus.ACTIVE,
    )
    session.add(cp)
    session.commit()
    session.refresh(cp)
    return e, cp


def test_counterparties_filter_by_entity_id(
    client: TestClient, db_session: Session, auth_user_admin: User,
) -> None:
    e1, cp1 = _seed_entity_with_counterparty(
        db_session, user=auth_user_admin,
        entity_name="SAS Alpha", cp_name="ACME Alpha",
    )
    e2, cp2 = _seed_entity_with_counterparty(
        db_session, user=auth_user_admin,
        entity_name="SAS Beta", cp_name="ACME Beta",
    )

    # Sans filtre : 2 contreparties
    resp_all = client.get("/api/counterparties")
    assert resp_all.status_code == 200
    assert len(resp_all.json()) == 2

    # Avec filtre entity_id=e1.id
    resp = client.get("/api/counterparties", params={"entity_id": e1.id})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["id"] == cp1.id

    resp2 = client.get("/api/counterparties", params={"entity_id": e2.id})
    assert resp2.status_code == 200
    assert resp2.json()[0]["id"] == cp2.id


def test_counterparties_entity_id_without_access_is_forbidden(
    client: TestClient, db_session: Session, auth_user_reader: User,
) -> None:
    e_other = Entity(name="SAS Interdite", legal_name="SAS Interdite")
    db_session.add(e_other)
    db_session.commit()

    resp = client.get("/api/counterparties", params={"entity_id": e_other.id})
    assert resp.status_code == 403
