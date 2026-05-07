"""Tests pour GET /api/analysis/mom et /api/analysis/mom/export (Plan I2).

Couvre :
1. Endpoint répond 200 avec entity_id valide.
2. Avec 6+ mois de data : retourne 6 points dans l'ordre chronologique.
3. Avec 3 mois de data : retourne 6 slots (dont 3 vides) + available_months=3.
4. Aucune data : retourne tableau vide + available_months=0.
5. Reader sur entity hors accès : 403.
6. Export CSV : statut 200, en-têtes corrects.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.entity import Entity
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction, TransactionCategorizationSource
from app.models.user import User
from app.models.user_entity_access import UserEntityAccess


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mk_entity_with_access(db: Session, user: User, name: str) -> tuple[Entity, BankAccount]:
    entity = Entity(name=name, legal_name=name)
    db.add(entity)
    db.flush()
    access = UserEntityAccess(user_id=user.id, entity_id=entity.id)
    ba = BankAccount(
        entity_id=entity.id,
        bank_code="delubac",
        bank_name="Delubac",
        iban=f"FR76MOM{entity.id:020d}",
        name=f"Compte MoM {name}",
    )
    db.add_all([access, ba])
    db.flush()
    return entity, ba


def _mk_tx(
    db: Session,
    ba: BankAccount,
    op_date: date,
    amount: Decimal,
    suffix: str,
) -> Transaction:
    ir = ImportRecord(
        bank_account_id=ba.id,
        bank_code=ba.bank_code,
        status=ImportStatus.COMPLETED,
        period_start=op_date.replace(day=1),
        period_end=op_date,
        opening_balance=Decimal("0"),
        closing_balance=amount,
        imported_count=1,
    )
    db.add(ir)
    db.flush()
    tx = Transaction(
        bank_account_id=ba.id,
        import_id=ir.id,
        operation_date=op_date,
        value_date=op_date,
        amount=amount,
        label=f"TX MoM {suffix}",
        raw_label=f"TX MoM {suffix}",
        dedup_key=f"mom-{ba.id}-{suffix}",
        statement_row_index=1,
        is_aggregation_parent=False,
        normalized_label=f"tx mom {suffix}",
        categorized_by=TransactionCategorizationSource.NONE,
    )
    db.add(tx)
    db.flush()
    return tx


def _add_months(d: date, n: int) -> date:
    """Helper pour naviguer dans les mois."""
    d = d.replace(day=1)
    total = d.year * 12 + (d.month - 1) + n
    year, month_idx = divmod(total, 12)
    return date(year, month_idx + 1, 1)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_mom_empty_entity_returns_empty(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """Entité avec compte mais sans transaction → available_months=0, 6 slots vides."""
    entity, _ba = _mk_entity_with_access(db_session, auth_user, "MoM Empty")
    db_session.commit()

    resp = client.get(f"/api/analysis/mom?entity_id={entity.id}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["available_months"] == 0
    # 6 slots retournés même sans data (fenêtre fixe)
    assert len(data["series"]) == 6
    for pt in data["series"]:
        assert pt["revenues_cents"] == 0
        assert pt["expenses_cents"] == 0


def test_mom_three_months_data(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """3 mois de data → available_months=3, 6 slots retournés (3 vides)."""
    # On ancre sur aujourd'hui en créant une tx "today" pour fixer l'ancre
    today = date.today()
    # Les 3 mois avec data : M-1, M-2, M-3 par rapport à today (mois de l'ancre)
    anchor_month = today.replace(day=15)
    months_with_data = [
        _add_months(anchor_month, -1),
        _add_months(anchor_month, -2),
        _add_months(anchor_month, -3),
    ]

    entity, ba = _mk_entity_with_access(db_session, auth_user, "MoM Three")
    # Créer une tx dans le mois courant pour fixer l'ancre
    _mk_tx(db_session, ba, anchor_month, Decimal("100"), "anchor")
    for i, m in enumerate(months_with_data):
        day = m.replace(day=10)
        _mk_tx(db_session, ba, day, Decimal("1000"), f"3m-{i}")
    db_session.commit()

    resp = client.get(f"/api/analysis/mom?entity_id={entity.id}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # 6 slots toujours (fenêtre fixe de 6 mois)
    assert len(data["series"]) == 6
    assert data["available_months"] == 3


def test_mom_six_months_data_returns_six_points(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """6 mois de data → 6 points avec revenues/expenses, ordered chronologically."""
    today = date.today()
    anchor_month = today.replace(day=20)

    entity, ba = _mk_entity_with_access(db_session, auth_user, "MoM Six")
    # Ancre
    _mk_tx(db_session, ba, anchor_month, Decimal("500"), "anchor6")
    # 6 mois finis
    for i in range(1, 7):
        day = _add_months(anchor_month, -i).replace(day=10)
        _mk_tx(db_session, ba, day, Decimal("2000"), f"6m-in-{i}")
        day2 = _add_months(anchor_month, -i).replace(day=20)
        _mk_tx(db_session, ba, day2, Decimal("-500"), f"6m-out-{i}")
    db_session.commit()

    resp = client.get(f"/api/analysis/mom?entity_id={entity.id}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    series = data["series"]
    assert len(series) == 6
    assert data["available_months"] == 6

    # Ordre chronologique : premier point = M-6
    months_list = [pt["month"] for pt in series]
    assert months_list == sorted(months_list)

    # Chaque point a revenues > 0 et expenses > 0
    for pt in series:
        assert pt["revenues_cents"] > 0
        assert pt["expenses_cents"] > 0
        assert pt["net_cents"] == pt["revenues_cents"] - pt["expenses_cents"]

    # Premier point : delta_pct = None (pas de précédent)
    assert series[0]["delta_revenues_pct"] is None
    assert series[0]["delta_expenses_pct"] is None

    # Points suivants : delta_pct calculé
    for pt in series[1:]:
        assert pt["delta_revenues_pct"] is not None


def test_mom_403_unauthorized_entity(
    client: TestClient,
    auth_user_reader: User,
    db_session: Session,
) -> None:
    """Reader sur entité sans accès → 403."""
    other = Entity(name="MoM Other", legal_name="MoM Other")
    db_session.add(other)
    db_session.commit()

    resp = client.get(f"/api/analysis/mom?entity_id={other.id}")
    assert resp.status_code == 403


def test_mom_export_csv(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """Export CSV MoM → statut 200, en-têtes corrects."""
    entity, _ba = _mk_entity_with_access(db_session, auth_user, "MoM Export")
    db_session.commit()

    resp = client.get(f"/api/analysis/mom/export?entity_id={entity.id}")
    assert resp.status_code == 200, resp.text
    assert "text/csv" in resp.headers["content-type"]
    assert "analyse-mom_" in resp.headers["content-disposition"]

    import csv, io
    text = resp.content.decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text), delimiter=";"))
    assert rows[0][0] == "Mois"
    assert rows[0][1] == "Encaissements (EUR)"
