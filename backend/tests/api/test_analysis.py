"""Tests pour /api/analysis/* — 6 endpoints KPI."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.category import Category
from app.models.counterparty import Counterparty, CounterpartyStatus
from app.models.entity import Entity
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction
from app.models.user import User
from app.models.user_entity_access import UserEntityAccess


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _today_first() -> date:
    return date.today().replace(day=1)


def _add_months(d: date, months: int) -> date:
    d = d.replace(day=1)
    total = d.year * 12 + (d.month - 1) + months
    year, m_idx = divmod(total, 12)
    return date(year, m_idx + 1, 1)


@pytest.fixture()
def other_entity(db_session: Session) -> Entity:
    e = Entity(name="Inaccessible", legal_name="Inaccessible SAS")
    db_session.add(e)
    db_session.commit()
    db_session.refresh(e)
    return e


@pytest.fixture()
def categories(db_session: Session) -> dict[str, Category]:
    out = {}
    for slug, name in (
        ("sales", "Ventes"),
        ("rent", "Loyer"),
        ("salaries", "Salaires"),
    ):
        # Catégories peuvent exister déjà (seed). Chercher ou créer.
        c = db_session.query(Category).filter_by(slug=slug).first()
        if c is None:
            c = Category(slug=slug, name=name)
            db_session.add(c)
            db_session.flush()
        out[slug] = c
    db_session.commit()
    return out


def _mk_import(
    db: Session, ba: BankAccount, *,
    closing: Decimal | None = None, period_end: date | None = None,
) -> ImportRecord:
    rec = ImportRecord(
        bank_account_id=ba.id,
        bank_code="delubac",
        status=ImportStatus.COMPLETED,
        closing_balance=closing,
        period_end=period_end,
    )
    db.add(rec)
    db.flush()
    return rec


def _mk_tx(
    db: Session,
    ba: BankAccount,
    *,
    amount: Decimal,
    op_date: date,
    category_id: int | None = None,
    counterparty_id: int | None = None,
    label: str = "tx",
) -> Transaction:
    rec = _mk_import(db, ba)
    tx = Transaction(
        bank_account_id=ba.id,
        import_id=rec.id,
        operation_date=op_date,
        value_date=op_date,
        amount=amount,
        label=label,
        raw_label=label,
        normalized_label=label.lower(),
        dedup_key=f"k-{label}-{op_date}-{amount}-{ba.id}",
        statement_row_index=0,
        category_id=category_id,
        counterparty_id=counterparty_id,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


# ---------------------------------------------------------------------------
# 1. Category drift
# ---------------------------------------------------------------------------


class TestCategoryDrift:
    def test_happy_path_alerts(
        self,
        client: TestClient,
        db_session: Session,
        auth_user_with_bank_account: dict,
        categories: dict[str, Category],
    ) -> None:
        e = auth_user_with_bank_account["entity"]
        ba = auth_user_with_bank_account["bank_account"]
        current = _today_first()

        # Sales : 1000 en moyenne sur 3m, 5000 ce mois → alert
        for i in range(1, 4):
            _mk_tx(
                db_session, ba,
                amount=Decimal("1000"),
                op_date=_add_months(current, -i) + (date.today() - current),
                category_id=categories["sales"].id,
                label=f"s-{i}",
            )
        _mk_tx(
            db_session, ba,
            amount=Decimal("5000"),
            op_date=date.today(),
            category_id=categories["sales"].id,
            label="s-cur",
        )
        # Loyer : stable à -1500
        for i in range(0, 4):
            _mk_tx(
                db_session, ba,
                amount=Decimal("-1500"),
                op_date=_add_months(current, -i) + (date.today() - current)
                if i > 0 else date.today(),
                category_id=categories["rent"].id,
                label=f"r-{i}",
            )

        r = client.get(f"/api/analysis/category-drift?entity_id={e.id}&seuil_pct=20")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["seuil_pct"] == 20.0
        labels = [row["label"] for row in body["rows"]]
        assert "Ventes" in labels
        # Ventes : current 500000, avg3m 100000 → delta 400%
        sales = next(r for r in body["rows"] if r["label"] == "Ventes")
        assert sales["status"] == "alert"
        assert sales["current_cents"] == 500000
        assert sales["avg3m_cents"] == 100000

    def test_403_on_inaccessible_entity(
        self, client: TestClient, auth_user_reader: User, other_entity: Entity,
    ) -> None:
        r = client.get(
            f"/api/analysis/category-drift?entity_id={other_entity.id}"
        )
        assert r.status_code == 403

    def test_empty(
        self, client: TestClient, auth_user_with_bank_account: dict,
    ) -> None:
        e = auth_user_with_bank_account["entity"]
        r = client.get(f"/api/analysis/category-drift?entity_id={e.id}")
        assert r.status_code == 200
        assert r.json() == {"rows": [], "seuil_pct": 20.0}


# ---------------------------------------------------------------------------
# 2. Top movers
# ---------------------------------------------------------------------------


class TestTopMovers:
    def test_happy_path(
        self,
        client: TestClient,
        db_session: Session,
        auth_user_with_bank_account: dict,
        categories: dict[str, Category],
    ) -> None:
        e = auth_user_with_bank_account["entity"]
        ba = auth_user_with_bank_account["bank_account"]
        current = _today_first()
        prev = _add_months(current, -1)

        # Sales : prev 1000, current 3000 → +2000
        _mk_tx(
            db_session, ba, amount=Decimal("1000"),
            op_date=prev + (date.today() - current),
            category_id=categories["sales"].id, label="sp",
        )
        _mk_tx(
            db_session, ba, amount=Decimal("3000"),
            op_date=date.today(),
            category_id=categories["sales"].id, label="sc",
        )
        # Salaires : prev -5000, current -8000 → -3000
        _mk_tx(
            db_session, ba, amount=Decimal("-5000"),
            op_date=prev + (date.today() - current),
            category_id=categories["salaries"].id, label="wp",
        )
        _mk_tx(
            db_session, ba, amount=Decimal("-8000"),
            op_date=date.today(),
            category_id=categories["salaries"].id, label="wc",
        )

        r = client.get(f"/api/analysis/top-movers?entity_id={e.id}&limit=5")
        assert r.status_code == 200, r.text
        body = r.json()
        assert len(body["increases"]) >= 1
        assert len(body["decreases"]) >= 1
        inc = body["increases"][0]
        assert inc["label"] == "Ventes"
        assert inc["delta_cents"] == 200000
        assert inc["direction"] == "in"
        assert len(inc["sparkline_3m_cents"]) == 3
        dec = body["decreases"][0]
        assert dec["label"] == "Salaires"
        assert dec["delta_cents"] == -300000
        assert dec["direction"] == "out"

    def test_403(
        self, client: TestClient, auth_user_reader: User, other_entity: Entity,
    ) -> None:
        r = client.get(f"/api/analysis/top-movers?entity_id={other_entity.id}")
        assert r.status_code == 403

    def test_empty(
        self, client: TestClient, auth_user_with_bank_account: dict,
    ) -> None:
        e = auth_user_with_bank_account["entity"]
        r = client.get(f"/api/analysis/top-movers?entity_id={e.id}")
        assert r.status_code == 200
        assert r.json() == {"increases": [], "decreases": []}


# ---------------------------------------------------------------------------
# 3. Runway
# ---------------------------------------------------------------------------


class TestRunway:
    def test_happy_path_burning(
        self,
        client: TestClient,
        db_session: Session,
        auth_user_with_bank_account: dict,
        categories: dict[str, Category],
    ) -> None:
        e = auth_user_with_bank_account["entity"]
        ba = auth_user_with_bank_account["bank_account"]
        current = _today_first()

        # 3 mois passés : flux net = -1000 chacun → burn = -1000 → -100000 cents
        for i in range(1, 4):
            m = _add_months(current, -i)
            _mk_tx(
                db_session, ba, amount=Decimal("-1000"),
                op_date=m + (date.today() - current),
                category_id=categories["salaries"].id, label=f"b-{i}",
            )

        # Solde actuel : 5000€
        _mk_import(
            db_session, ba,
            closing=Decimal("5000"),
            period_end=date.today().replace(day=1),
        )
        db_session.commit()

        r = client.get(f"/api/analysis/runway?entity_id={e.id}")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["burn_rate_cents"] == -100000
        assert body["current_balance_cents"] == 500000
        assert body["runway_months"] == 5
        assert len(body["forecast_balance_6m_cents"]) == 6
        assert body["status"] in ("warning", "critical")

    def test_403(
        self, client: TestClient, auth_user_reader: User, other_entity: Entity,
    ) -> None:
        r = client.get(f"/api/analysis/runway?entity_id={other_entity.id}")
        assert r.status_code == 403

    def test_empty(
        self, client: TestClient, auth_user_with_bank_account: dict,
    ) -> None:
        e = auth_user_with_bank_account["entity"]
        r = client.get(f"/api/analysis/runway?entity_id={e.id}")
        assert r.status_code == 200
        body = r.json()
        assert body["burn_rate_cents"] == 0
        assert body["current_balance_cents"] == 0
        assert body["runway_months"] is None
        assert body["status"] == "none"


# ---------------------------------------------------------------------------
# 4. YoY
# ---------------------------------------------------------------------------


class TestYoY:
    def test_happy_path(
        self,
        client: TestClient,
        db_session: Session,
        auth_user_with_bank_account: dict,
    ) -> None:
        e = auth_user_with_bank_account["entity"]
        ba = auth_user_with_bank_account["bank_account"]
        current = _today_first()

        # Revenus ce mois : 2000
        _mk_tx(
            db_session, ba, amount=Decimal("2000"),
            op_date=date.today(), label="r-cur",
        )
        # Revenus mois-12 : 1500
        m_minus_12 = _add_months(current, -12)
        _mk_tx(
            db_session, ba, amount=Decimal("1500"),
            op_date=m_minus_12, label="r-prev",
        )
        # Dépenses ce mois : -500
        _mk_tx(
            db_session, ba, amount=Decimal("-500"),
            op_date=date.today(), label="e-cur",
        )

        r = client.get(f"/api/analysis/yoy?entity_id={e.id}")
        assert r.status_code == 200, r.text
        body = r.json()
        assert len(body["months"]) == 12
        assert len(body["series"]) == 12
        last = body["series"][-1]
        assert last["revenues_current"] == 200000
        assert last["revenues_previous"] == 150000
        assert last["expenses_current"] == 50000

    def test_403(
        self, client: TestClient, auth_user_reader: User, other_entity: Entity,
    ) -> None:
        r = client.get(f"/api/analysis/yoy?entity_id={other_entity.id}")
        assert r.status_code == 403

    def test_empty(
        self, client: TestClient, auth_user_with_bank_account: dict,
    ) -> None:
        e = auth_user_with_bank_account["entity"]
        r = client.get(f"/api/analysis/yoy?entity_id={e.id}")
        assert r.status_code == 200
        body = r.json()
        assert len(body["months"]) == 12
        # All zeros
        for pt in body["series"]:
            assert pt["revenues_current"] == 0
            assert pt["revenues_previous"] == 0


# ---------------------------------------------------------------------------
# 5. Client concentration
# ---------------------------------------------------------------------------


class TestClientConcentration:
    def test_happy_path(
        self,
        client: TestClient,
        db_session: Session,
        auth_user_with_bank_account: dict,
    ) -> None:
        e = auth_user_with_bank_account["entity"]
        ba = auth_user_with_bank_account["bank_account"]

        # 3 clients
        cps = []
        for name in ("Acme", "Beta", "Gamma"):
            cp = Counterparty(
                entity_id=e.id, name=name, normalized_name=name.lower(),
                status=CounterpartyStatus.ACTIVE,
            )
            db_session.add(cp)
            db_session.flush()
            cps.append(cp)
        db_session.commit()

        # Acme domine avec 8000, Beta 1500, Gamma 500
        _mk_tx(
            db_session, ba, amount=Decimal("8000"),
            op_date=date.today(), counterparty_id=cps[0].id, label="a",
        )
        _mk_tx(
            db_session, ba, amount=Decimal("1500"),
            op_date=date.today(), counterparty_id=cps[1].id, label="b",
        )
        _mk_tx(
            db_session, ba, amount=Decimal("500"),
            op_date=date.today(), counterparty_id=cps[2].id, label="g",
        )

        r = client.get(
            f"/api/analysis/client-concentration?entity_id={e.id}&months=12"
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total_revenue_cents"] == 1000000
        assert len(body["top5"]) == 3
        assert body["top5"][0]["name"] == "Acme"
        assert body["top5"][0]["share_pct"] == 80.0
        assert body["others_cents"] == 0
        assert body["hhi"] > 6000  # 80² + 15² + 5² = 6450
        assert body["risk_level"] == "high"

    def test_403(
        self, client: TestClient, auth_user_reader: User, other_entity: Entity,
    ) -> None:
        r = client.get(
            f"/api/analysis/client-concentration?entity_id={other_entity.id}"
        )
        assert r.status_code == 403

    def test_empty(
        self, client: TestClient, auth_user_with_bank_account: dict,
    ) -> None:
        e = auth_user_with_bank_account["entity"]
        r = client.get(
            f"/api/analysis/client-concentration?entity_id={e.id}"
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total_revenue_cents"] == 0
        assert body["top5"] == []
        assert body["risk_level"] == "low"


# ---------------------------------------------------------------------------
# 6. Entities comparison
# ---------------------------------------------------------------------------


class TestEntitiesComparison:
    def test_happy_path(
        self,
        client: TestClient,
        db_session: Session,
        auth_user_with_bank_account: dict,
    ) -> None:
        ba = auth_user_with_bank_account["bank_account"]

        _mk_tx(
            db_session, ba, amount=Decimal("1000"),
            op_date=date.today(), label="rev",
        )
        _mk_tx(
            db_session, ba, amount=Decimal("-400"),
            op_date=date.today(), label="exp",
        )

        r = client.get("/api/analysis/entities-comparison?months=1")
        assert r.status_code == 200, r.text
        body = r.json()
        assert len(body["entities"]) == 1
        row = body["entities"][0]
        assert row["revenues_cents"] == 100000
        assert row["expenses_cents"] == 40000
        assert row["net_variation_cents"] == 60000

    def test_empty_no_entities(
        self, client: TestClient, auth_user: User,
    ) -> None:
        """User without any UserEntityAccess → empty list."""
        r = client.get("/api/analysis/entities-comparison")
        assert r.status_code == 200
        assert r.json() == {"entities": []}

    def test_multi_entities_ordered(
        self,
        client: TestClient,
        db_session: Session,
        auth_user_with_bank_account: dict,
    ) -> None:
        user = auth_user_with_bank_account["user"]
        # Ajouter une seconde entité accessible
        e2 = Entity(name="Aaa Society", legal_name="Aaa SAS")
        db_session.add(e2)
        db_session.flush()
        db_session.add(UserEntityAccess(user_id=user.id, entity_id=e2.id))
        db_session.commit()

        r = client.get("/api/analysis/entities-comparison")
        assert r.status_code == 200
        body = r.json()
        assert len(body["entities"]) == 2
        # Tri alphabétique : Aaa avant SAS Horizon Test
        assert body["entities"][0]["name"] == "Aaa Society"
