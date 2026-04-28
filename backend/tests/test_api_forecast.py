"""Tests de /api/forecast/* (entries CRUD + projection)."""
from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.entity import Entity
from app.models.forecast_entry import ForecastEntry, ForecastRecurrence
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


class TestForecastEntries:
    def test_create_list_update_delete(
        self, client: TestClient, auth_user: User, db_session: Session,
    ) -> None:
        e, _ba = _mk_entity_access(db_session, user=auth_user)

        payload = {
            "entity_id": e.id,
            "label": "Loyer bureau",
            "amount": "-1500.00",
            "due_date": (date.today() + timedelta(days=5)).isoformat(),
            "recurrence": "MONTHLY",
        }
        r = client.post("/api/forecast/entries", json=payload)
        assert r.status_code == 201, r.text
        entry = r.json()
        assert entry["label"] == "Loyer bureau"
        assert entry["recurrence"] == "MONTHLY"
        entry_id = entry["id"]

        r = client.get(f"/api/forecast/entries?entity_id={e.id}")
        assert r.status_code == 200
        assert len(r.json()) == 1

        r = client.patch(
            f"/api/forecast/entries/{entry_id}",
            json={"label": "Loyer bureau Q2"},
        )
        assert r.status_code == 200
        assert r.json()["label"] == "Loyer bureau Q2"

        r = client.delete(f"/api/forecast/entries/{entry_id}")
        assert r.status_code == 204
        r = client.get(f"/api/forecast/entries?entity_id={e.id}")
        assert r.json() == []

    def test_cannot_create_for_inaccessible_entity(
        self, client: TestClient, auth_user_reader: User, db_session: Session,
    ) -> None:
        other = Entity(name="Other", legal_name="Other")
        db_session.add(other)
        db_session.commit()

        r = client.post(
            "/api/forecast/entries",
            json={
                "entity_id": other.id,
                "label": "X",
                "amount": "100.00",
                "due_date": date.today().isoformat(),
            },
        )
        assert r.status_code == 403


class TestForecastProjection:
    def test_projects_monthly_recurrence(
        self, client: TestClient, auth_user: User, db_session: Session,
    ) -> None:
        e, _ba = _mk_entity_access(db_session, user=auth_user)
        db_session.add(
            ForecastEntry(
                entity_id=e.id,
                label="Salaire",
                amount=Decimal("3000"),
                due_date=date.today() + timedelta(days=10),
                recurrence=ForecastRecurrence.MONTHLY,
            )
        )
        db_session.commit()

        r = client.get(f"/api/forecast/projection?horizon_days=90&entity_id={e.id}")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["horizon_days"] == 90
        assert len(body["points"]) == 91

        planned_total = sum(
            Decimal(p["planned_net"]) for p in body["points"]
        )
        # Sur 90 jours à partir d'aujourd'hui, MONTHLY à J+10 → 3 occurrences
        # (J+10, J+40, J+70, éventuellement J+100 hors horizon).
        assert planned_total == Decimal("9000.00")
