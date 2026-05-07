"""POST /api/commitments/bulk-cancel basculer plusieurs engagements en cancelled."""
from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.commitment import Commitment, CommitmentDirection, CommitmentStatus


def _c(e_id: int, status: CommitmentStatus = CommitmentStatus.PENDING) -> Commitment:
    today = date.today()
    return Commitment(
        entity_id=e_id,
        direction=CommitmentDirection.IN,
        amount_cents=100,
        issue_date=today - timedelta(days=30),
        expected_date=today,
        status=status,
    )


def test_bulk_cancel_pending_commitments(
    client: TestClient,
    db_session: Session,
    auth_user_with_bank_account,
) -> None:
    e_id = auth_user_with_bank_account["bank_account"].entity_id
    a, b, already = _c(e_id), _c(e_id), _c(e_id, status=CommitmentStatus.CANCELLED)
    db_session.add_all([a, b, already])
    db_session.commit()

    resp = client.post(
        "/api/commitments/bulk-cancel",
        json={"ids": [a.id, b.id, already.id]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["cancelled"] == 2
    db_session.expire_all()
    assert db_session.get(Commitment, a.id).status == CommitmentStatus.CANCELLED
    assert db_session.get(Commitment, b.id).status == CommitmentStatus.CANCELLED


def test_bulk_cancel_rejects_cross_entity(
    client: TestClient,
    db_session: Session,
    auth_user_reader,
) -> None:
    """Si un id n'appartient pas à une entité accessible, refuser globalement.

    Use le rôle READER : `auth_user` est ADMIN et a donc accès à TOUTES les
    entités via `accessible_entity_ids_subquery`, ce qui rend la vérif
    cross-entity vacante. Avec READER on contrôle finement le périmètre.
    """
    from app.models.entity import Entity
    from app.models.user_entity_access import UserEntityAccess

    own = Entity(name="Mienne", legal_name="Mienne SARL")
    other = Entity(name="Autre", legal_name="Autre SARL")
    db_session.add_all([own, other])
    db_session.flush()
    db_session.add(UserEntityAccess(user_id=auth_user_reader.id, entity_id=own.id))
    a = _c(own.id)
    forbidden = _c(other.id)
    db_session.add_all([a, forbidden])
    db_session.commit()

    resp = client.post(
        "/api/commitments/bulk-cancel",
        json={"ids": [a.id, forbidden.id]},
    )
    assert resp.status_code == 403
