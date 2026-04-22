"""Tests API /api/forecast/pivot (Plan 5b Phase 5)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.category import Category
from app.models.entity import Entity
from app.models.forecast_line import ForecastLine, ForecastLineMethod
from app.models.forecast_scenario import ForecastScenario
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction
from app.models.user import User
from app.models.user_entity_access import UserEntityAccess
from app.services.forecast_engine import _add_months, _first_of_month


@pytest.fixture()
def pivot_ctx(db_session: Session, auth_user: User) -> dict:
    """Entité accessible + 2 comptes + 2 catégories + historique + 1 ligne forecast."""
    e = Entity(name="EPivot", legal_name="EPivot")
    db_session.add(e)
    db_session.flush()
    db_session.add(UserEntityAccess(user_id=auth_user.id, entity_id=e.id))

    ba1 = BankAccount(
        entity_id=e.id,
        bank_code="delubac",
        bank_name="Delubac",
        iban="FR7600000000000000000000711",
        name="Compte Pivot 1",
    )
    ba2 = BankAccount(
        entity_id=e.id,
        bank_code="delubac",
        bank_name="Delubac",
        iban="FR7600000000000000000000712",
        name="Compte Pivot 2",
    )
    db_session.add_all([ba1, ba2])
    db_session.flush()

    sc = ForecastScenario(entity_id=e.id, name="Principal", is_default=True)
    db_session.add(sc)
    db_session.flush()

    sal = Category(name="SalairesPivot", slug="salaires-pivot")
    ven = Category(name="VentesPivot", slug="ventes-pivot")
    db_session.add_all([sal, ven])
    db_session.flush()

    ir = ImportRecord(
        bank_account_id=ba1.id,
        bank_code="delubac",
        filename="pivot.pdf",
        status=ImportStatus.COMPLETED,
        imported_count=0,
    )
    db_session.add(ir)
    db_session.flush()

    current_first = _first_of_month(date.today())
    # 6 mois d'historique pour stabiliser AVG_3M
    for i in range(1, 7):
        m = _add_months(current_first, -i)
        op = date(m.year, m.month, 10)
        db_session.add(
            Transaction(
                bank_account_id=ba1.id,
                import_id=ir.id,
                operation_date=op,
                value_date=op,
                amount=Decimal("-3000.00"),
                label=f"Sal {m}",
                raw_label=f"Sal {m}",
                dedup_key=f"sal-piv-{op.isoformat()}",
                statement_row_index=i * 2,
                category_id=sal.id,
                normalized_label=f"sal {m}",
            )
        )
        db_session.add(
            Transaction(
                bank_account_id=ba1.id,
                import_id=ir.id,
                operation_date=op,
                value_date=op,
                amount=Decimal("5000.00"),
                label=f"Ven {m}",
                raw_label=f"Ven {m}",
                dedup_key=f"ven-piv-{op.isoformat()}",
                statement_row_index=i * 2 + 1,
                category_id=ven.id,
                normalized_label=f"ven {m}",
            )
        )
    # Un mouvement sur ba2 pour pouvoir tester le filtre accounts
    op2 = date(
        _add_months(current_first, -1).year,
        _add_months(current_first, -1).month,
        15,
    )
    db_session.add(
        Transaction(
            bank_account_id=ba2.id,
            import_id=ir.id,
            operation_date=op2,
            value_date=op2,
            amount=Decimal("1234.00"),
            label="Autre ba2",
            raw_label="Autre ba2",
            dedup_key=f"ba2-{op2.isoformat()}",
            statement_row_index=999,
            category_id=ven.id,
            normalized_label="autre ba2",
        )
    )

    # Une ligne forecast AVG_3M sur Salaires (mois courant et futur)
    db_session.add(
        ForecastLine(
            scenario_id=sc.id,
            entity_id=e.id,
            category_id=sal.id,
            method=ForecastLineMethod.AVG_3M,
        )
    )
    db_session.commit()
    db_session.refresh(e)
    db_session.refresh(sc)
    db_session.refresh(ba1)
    db_session.refresh(ba2)
    db_session.refresh(sal)
    db_session.refresh(ven)
    return {
        "entity": e,
        "scenario": sc,
        "ba1": ba1,
        "ba2": ba2,
        "salaires": sal,
        "ventes": ven,
        "current_month": current_first,
    }


@pytest.fixture()
def foreign_scenario(db_session: Session) -> ForecastScenario:
    e = Entity(name="EForPivot", legal_name="EForPivot")
    db_session.add(e)
    db_session.flush()
    sc = ForecastScenario(entity_id=e.id, name="Autre", is_default=True)
    db_session.add(sc)
    db_session.commit()
    db_session.refresh(sc)
    return sc


def _month_str(d: date) -> str:
    return d.strftime("%Y-%m")


class TestPivotEndpoint:
    def test_happy_path(self, client: TestClient, pivot_ctx: dict) -> None:
        cur = pivot_ctx["current_month"]
        frm = _month_str(_add_months(cur, -2))
        to = _month_str(_add_months(cur, 1))
        r = client.get(
            "/api/forecast/pivot",
            params={
                "scenario_id": pivot_ctx["scenario"].id,
                "entity_id": pivot_ctx["entity"].id,
                "from": frm,
                "to": to,
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["months"][0] == frm
        assert body["months"][-1] == to
        assert len(body["months"]) == 4
        # 2 catégories avec historique → au moins 2 lignes
        labels = {row["label"] for row in body["rows"]}
        assert "SalairesPivot" in labels
        assert "VentesPivot" in labels
        # Chaque row a len(cells) == len(months)
        for row in body["rows"]:
            assert len(row["cells"]) == len(body["months"])
            for cell in row["cells"]:
                assert "realized_cents" in cell
                assert "committed_cents" in cell
                assert "forecast_cents" in cell
                assert "total_cents" in cell
        # Séries cohérentes
        assert len(body["realized_series"]) == len(body["months"])
        assert len(body["forecast_series"]) == len(body["months"])
        for pt in body["realized_series"]:
            assert "in_cents" in pt and "out_cents" in pt
        # Cache header
        assert "private" in r.headers["cache-control"].lower()

    def test_forbidden_entity(
        self, client: TestClient, pivot_ctx: dict, db_session: Session
    ) -> None:
        other = Entity(name="NoAccess", legal_name="NoAccess")
        db_session.add(other)
        db_session.commit()
        cur = pivot_ctx["current_month"]
        r = client.get(
            "/api/forecast/pivot",
            params={
                "scenario_id": pivot_ctx["scenario"].id,
                "entity_id": other.id,
                "from": _month_str(cur),
                "to": _month_str(cur),
            },
        )
        assert r.status_code == 403

    def test_scenario_not_matching_entity(
        self, client: TestClient, pivot_ctx: dict, foreign_scenario: ForecastScenario
    ) -> None:
        cur = pivot_ctx["current_month"]
        r = client.get(
            "/api/forecast/pivot",
            params={
                "scenario_id": foreign_scenario.id,
                "entity_id": pivot_ctx["entity"].id,
                "from": _month_str(cur),
                "to": _month_str(cur),
            },
        )
        assert r.status_code == 403

    def test_range_too_wide(self, client: TestClient, pivot_ctx: dict) -> None:
        cur = pivot_ctx["current_month"]
        frm = _month_str(cur)
        to = _month_str(_add_months(cur, 40))
        r = client.get(
            "/api/forecast/pivot",
            params={
                "scenario_id": pivot_ctx["scenario"].id,
                "entity_id": pivot_ctx["entity"].id,
                "from": frm,
                "to": to,
            },
        )
        assert r.status_code == 400
        assert "36" in r.json()["detail"]

    def test_from_after_to(self, client: TestClient, pivot_ctx: dict) -> None:
        cur = pivot_ctx["current_month"]
        r = client.get(
            "/api/forecast/pivot",
            params={
                "scenario_id": pivot_ctx["scenario"].id,
                "entity_id": pivot_ctx["entity"].id,
                "from": _month_str(_add_months(cur, 2)),
                "to": _month_str(cur),
            },
        )
        assert r.status_code == 400

    def test_invalid_month_format(self, client: TestClient, pivot_ctx: dict) -> None:
        r = client.get(
            "/api/forecast/pivot",
            params={
                "scenario_id": pivot_ctx["scenario"].id,
                "entity_id": pivot_ctx["entity"].id,
                "from": "2026-13",
                "to": "2026-14",
            },
        )
        assert r.status_code == 400

    def test_accounts_filter_reduces_realized(
        self, client: TestClient, pivot_ctx: dict
    ) -> None:
        cur = pivot_ctx["current_month"]
        frm = _month_str(_add_months(cur, -2))
        to = _month_str(cur)
        params_base = {
            "scenario_id": pivot_ctx["scenario"].id,
            "entity_id": pivot_ctx["entity"].id,
            "from": frm,
            "to": to,
        }
        # Sans filtre : inclut ba1 + ba2
        r_full = client.get("/api/forecast/pivot", params=params_base)
        assert r_full.status_code == 200
        # Avec filtre ba1 uniquement : exclut le mouvement 1234 sur ba2
        r_filt = client.get(
            "/api/forecast/pivot",
            params={**params_base, "accounts": str(pivot_ctx["ba1"].id)},
        )
        assert r_filt.status_code == 200
        full_in = sum(pt["in_cents"] for pt in r_full.json()["realized_series"])
        filt_in = sum(pt["in_cents"] for pt in r_filt.json()["realized_series"])
        assert full_in > filt_in
        assert full_in - filt_in == 123_400  # 1234€ * 100

    def test_accounts_invalid(self, client: TestClient, pivot_ctx: dict) -> None:
        cur = pivot_ctx["current_month"]
        r = client.get(
            "/api/forecast/pivot",
            params={
                "scenario_id": pivot_ctx["scenario"].id,
                "entity_id": pivot_ctx["entity"].id,
                "from": _month_str(cur),
                "to": _month_str(cur),
                "accounts": "99999",
            },
        )
        assert r.status_code == 400
