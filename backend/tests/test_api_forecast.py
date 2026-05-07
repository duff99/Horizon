"""Tests de /api/forecast/* (projection de trésorerie + suggestions de récurrences).

D1 : les routes /entries CRUD ont été supprimées. TestForecastEntries est retiré.
"""
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.entity import Entity
from app.models.user import User
from app.models.user_entity_access import UserEntityAccess


def _mk_entity_access(db: Session, *, user: User) -> tuple[Entity, BankAccount]:
    e = Entity(name="E1", legal_name="E1")
    db.add(e)
    db.flush()
    db.add(UserEntityAccess(user_id=user.id, entity_id=e.id))
    ba = BankAccount(
        entity_id=e.id,
        bank_code="delubac",
        bank_name="Delubac",
        iban=f"FR7630004000{user.id:016d}",
        name="Cpt",
    )
    db.add(ba)
    db.commit()
    db.refresh(ba)
    return e, ba


class TestForecastProjection:
    def test_projection_returns_flat_curve_since_d1(
        self, client: TestClient, auth_user: User, db_session: Session,
    ) -> None:
        """Depuis D1, forecast_entries n'existe plus. La projection retourne
        une courbe plate sur horizon_days+1 points avec planned_net=0."""
        e, _ba = _mk_entity_access(db_session, user=auth_user)

        r = client.get(f"/api/forecast/projection?horizon_days=90&entity_id={e.id}")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["horizon_days"] == 90
        assert len(body["points"]) == 91

        # Depuis D1, plus d'entrées manuelles : toutes les planned_net = 0
        for point in body["points"]:
            assert point["planned_net"] == "0", (
                f"planned_net doit être 0 (plus de ForecastEntry) — got {point['planned_net']}"
            )

    def test_projection_forbidden_for_inaccessible_entity(
        self, client: TestClient, auth_user_reader: User, db_session: Session,
    ) -> None:
        other = Entity(name="Other", legal_name="Other")
        db_session.add(other)
        db_session.commit()
        r = client.get(
            f"/api/forecast/projection?horizon_days=30&entity_id={other.id}"
        )
        assert r.status_code == 403
