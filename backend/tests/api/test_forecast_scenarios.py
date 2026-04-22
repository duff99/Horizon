"""Tests API /api/forecast/scenarios (Plan 5b Phase 3)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entity import Entity
from app.models.forecast_scenario import ForecastScenario
from app.models.user import User
from app.models.user_entity_access import UserEntityAccess


@pytest.fixture()
def entity_access(db_session: Session, auth_user: User) -> Entity:
    e = Entity(name="EScenarios", legal_name="EScenarios")
    db_session.add(e)
    db_session.flush()
    db_session.add(UserEntityAccess(user_id=auth_user.id, entity_id=e.id))
    db_session.commit()
    db_session.refresh(e)
    return e


@pytest.fixture()
def foreign_entity(db_session: Session) -> Entity:
    e = Entity(name="EForeign", legal_name="EForeign")
    db_session.add(e)
    db_session.commit()
    db_session.refresh(e)
    return e


class TestScenariosCRUD:
    def test_create_first_scenario(
        self, client: TestClient, entity_access: Entity
    ) -> None:
        r = client.post(
            "/api/forecast/scenarios",
            json={"entity_id": entity_access.id, "name": "Base", "is_default": True},
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["name"] == "Base"
        assert body["is_default"] is True

    def test_list_requires_access(
        self,
        client: TestClient,
        foreign_entity: Entity,
        auth_user: User,  # ensure login happened
    ) -> None:
        r = client.get(f"/api/forecast/scenarios?entity_id={foreign_entity.id}")
        assert r.status_code == 403

    def test_list_filters_by_entity(
        self, client: TestClient, entity_access: Entity, db_session: Session
    ) -> None:
        db_session.add(
            ForecastScenario(
                entity_id=entity_access.id, name="A", is_default=True
            )
        )
        db_session.add(
            ForecastScenario(
                entity_id=entity_access.id, name="B", is_default=False
            )
        )
        db_session.commit()
        r = client.get(f"/api/forecast/scenarios?entity_id={entity_access.id}")
        assert r.status_code == 200
        items = r.json()
        assert len(items) == 2
        # Default comes first
        assert items[0]["is_default"] is True

    def test_create_with_default_unflags_existing(
        self, client: TestClient, entity_access: Entity, db_session: Session
    ) -> None:
        old = ForecastScenario(
            entity_id=entity_access.id, name="Old", is_default=True
        )
        db_session.add(old)
        db_session.commit()
        db_session.refresh(old)

        r = client.post(
            "/api/forecast/scenarios",
            json={
                "entity_id": entity_access.id,
                "name": "New",
                "is_default": True,
            },
        )
        assert r.status_code == 201

        db_session.expire_all()
        refreshed = db_session.get(ForecastScenario, old.id)
        assert refreshed is not None
        assert refreshed.is_default is False

    def test_patch_toggle_default(
        self, client: TestClient, entity_access: Entity, db_session: Session
    ) -> None:
        a = ForecastScenario(entity_id=entity_access.id, name="A", is_default=True)
        b = ForecastScenario(entity_id=entity_access.id, name="B", is_default=False)
        db_session.add_all([a, b])
        db_session.commit()
        db_session.refresh(a)
        db_session.refresh(b)

        r = client.patch(
            f"/api/forecast/scenarios/{b.id}", json={"is_default": True}
        )
        assert r.status_code == 200
        assert r.json()["is_default"] is True

        db_session.expire_all()
        assert db_session.get(ForecastScenario, a.id).is_default is False
        assert db_session.get(ForecastScenario, b.id).is_default is True

    def test_delete_only_scenario_conflict(
        self, client: TestClient, entity_access: Entity, db_session: Session
    ) -> None:
        only = ForecastScenario(
            entity_id=entity_access.id, name="Only", is_default=True
        )
        db_session.add(only)
        db_session.commit()
        db_session.refresh(only)

        r = client.delete(f"/api/forecast/scenarios/{only.id}")
        assert r.status_code == 409

    def test_delete_default_promotes_other(
        self, client: TestClient, entity_access: Entity, db_session: Session
    ) -> None:
        a = ForecastScenario(entity_id=entity_access.id, name="A", is_default=True)
        b = ForecastScenario(entity_id=entity_access.id, name="B", is_default=False)
        db_session.add_all([a, b])
        db_session.commit()
        db_session.refresh(a)
        db_session.refresh(b)

        r = client.delete(f"/api/forecast/scenarios/{a.id}")
        assert r.status_code == 204

        db_session.expire_all()
        remaining = list(
            db_session.scalars(
                select(ForecastScenario).where(
                    ForecastScenario.entity_id == entity_access.id
                )
            )
        )
        assert len(remaining) == 1
        assert remaining[0].id == b.id
        assert remaining[0].is_default is True

    def test_delete_non_default_keeps_default(
        self, client: TestClient, entity_access: Entity, db_session: Session
    ) -> None:
        a = ForecastScenario(entity_id=entity_access.id, name="A", is_default=True)
        b = ForecastScenario(entity_id=entity_access.id, name="B", is_default=False)
        db_session.add_all([a, b])
        db_session.commit()
        db_session.refresh(a)
        db_session.refresh(b)

        r = client.delete(f"/api/forecast/scenarios/{b.id}")
        assert r.status_code == 204
        db_session.expire_all()
        assert db_session.get(ForecastScenario, a.id).is_default is True


class TestEntityCreateSeedsDefault:
    def test_post_entity_creates_default_scenario(
        self, client: TestClient, auth_user: User, db_session: Session
    ) -> None:
        # auth_user is ADMIN, POST /api/entities requires admin
        r = client.post(
            "/api/entities",
            json={"name": "NewCo", "legal_name": "NewCo SAS"},
        )
        assert r.status_code == 201, r.text
        entity_id = r.json()["id"]
        db_session.expire_all()
        sc = db_session.scalar(
            select(ForecastScenario).where(
                ForecastScenario.entity_id == entity_id,
                ForecastScenario.is_default.is_(True),
            )
        )
        assert sc is not None
        assert sc.name == "Principal"
