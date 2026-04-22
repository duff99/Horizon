"""Tests API /api/forecast/lines (Plan 5b Phase 3)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.entity import Entity
from app.models.forecast_line import ForecastLine
from app.models.forecast_scenario import ForecastScenario
from app.models.user import User
from app.models.user_entity_access import UserEntityAccess


@pytest.fixture()
def line_ctx(db_session: Session, auth_user: User) -> dict:
    e = Entity(name="ELines", legal_name="ELines")
    db_session.add(e)
    db_session.flush()
    db_session.add(UserEntityAccess(user_id=auth_user.id, entity_id=e.id))
    sc = ForecastScenario(entity_id=e.id, name="Base", is_default=True)
    db_session.add(sc)
    cat = Category(name="TestCat", slug="test-cat-lines-phase3")
    cat2 = Category(name="BaseCat", slug="base-cat-lines-phase3")
    db_session.add_all([cat, cat2])
    db_session.commit()
    db_session.refresh(e)
    db_session.refresh(sc)
    db_session.refresh(cat)
    db_session.refresh(cat2)
    return {"entity": e, "scenario": sc, "category": cat, "base_category": cat2}


class TestLinesCRUD:
    def test_upsert_creates_then_updates(
        self, client: TestClient, line_ctx: dict, db_session: Session
    ) -> None:
        sc = line_ctx["scenario"]
        cat = line_ctx["category"]
        payload = {
            "scenario_id": sc.id,
            "category_id": cat.id,
            "method": "RECURRING_FIXED",
            "amount_cents": 100_000,
        }
        r = client.put("/api/forecast/lines", json=payload)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["amount_cents"] == 100_000
        line_id = body["id"]

        # Second PUT = update (même scenario+category)
        payload["amount_cents"] = 150_000
        r = client.put("/api/forecast/lines", json=payload)
        assert r.status_code == 200
        assert r.json()["id"] == line_id
        assert r.json()["amount_cents"] == 150_000

        db_session.expire_all()
        count = len(
            list(
                db_session.scalars(
                    select(ForecastLine).where(
                        ForecastLine.scenario_id == sc.id,
                        ForecastLine.category_id == cat.id,
                    )
                )
            )
        )
        assert count == 1

    def test_upsert_recurring_missing_amount_422(
        self, client: TestClient, line_ctx: dict
    ) -> None:
        sc = line_ctx["scenario"]
        cat = line_ctx["category"]
        r = client.put(
            "/api/forecast/lines",
            json={
                "scenario_id": sc.id,
                "category_id": cat.id,
                "method": "RECURRING_FIXED",
            },
        )
        assert r.status_code == 422

    def test_upsert_based_on_category_ok(
        self, client: TestClient, line_ctx: dict
    ) -> None:
        sc = line_ctx["scenario"]
        cat = line_ctx["category"]
        base = line_ctx["base_category"]
        r = client.put(
            "/api/forecast/lines",
            json={
                "scenario_id": sc.id,
                "category_id": cat.id,
                "method": "BASED_ON_CATEGORY",
                "base_category_id": base.id,
                "ratio": "0.15",
            },
        )
        assert r.status_code == 200
        assert r.json()["base_category_id"] == base.id

    def test_upsert_formula_requires_expr(
        self, client: TestClient, line_ctx: dict
    ) -> None:
        sc = line_ctx["scenario"]
        cat = line_ctx["category"]
        r = client.put(
            "/api/forecast/lines",
            json={
                "scenario_id": sc.id,
                "category_id": cat.id,
                "method": "FORMULA",
            },
        )
        assert r.status_code == 422

    def test_delete_line(
        self, client: TestClient, line_ctx: dict, db_session: Session
    ) -> None:
        sc = line_ctx["scenario"]
        cat = line_ctx["category"]
        line = ForecastLine(
            scenario_id=sc.id,
            entity_id=sc.entity_id,
            category_id=cat.id,
            method="RECURRING_FIXED",
            amount_cents=1000,
        )
        db_session.add(line)
        db_session.commit()
        db_session.refresh(line)

        r = client.delete(f"/api/forecast/lines/{line.id}")
        assert r.status_code == 204
        db_session.expire_all()
        assert db_session.get(ForecastLine, line.id) is None

    def test_delete_non_existent_404(
        self, client: TestClient, line_ctx: dict
    ) -> None:
        # auth needed: entity access check happens after get, so ensure login
        r = client.delete("/api/forecast/lines/999999")
        assert r.status_code == 404

    def test_list_lines(
        self, client: TestClient, line_ctx: dict, db_session: Session
    ) -> None:
        sc = line_ctx["scenario"]
        cat = line_ctx["category"]
        db_session.add(
            ForecastLine(
                scenario_id=sc.id,
                entity_id=sc.entity_id,
                category_id=cat.id,
                method="AVG_3M",
            )
        )
        db_session.commit()
        r = client.get(f"/api/forecast/lines?scenario_id={sc.id}")
        assert r.status_code == 200
        assert len(r.json()) == 1


class TestValidateFormulaStub:
    def test_valid_non_empty_formula(
        self, client: TestClient, line_ctx: dict
    ) -> None:
        sc = line_ctx["scenario"]
        r = client.post(
            "/api/forecast/lines/validate-formula",
            json={"scenario_id": sc.id, "formula_expr": "cat(1) * 2"},
        )
        assert r.status_code == 200
        assert r.json()["valid"] is True

    def test_empty_formula_invalid(
        self, client: TestClient, line_ctx: dict
    ) -> None:
        sc = line_ctx["scenario"]
        r = client.post(
            "/api/forecast/lines/validate-formula",
            json={"scenario_id": sc.id, "formula_expr": "   "},
        )
        assert r.status_code == 200
        assert r.json()["valid"] is False
