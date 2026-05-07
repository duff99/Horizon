"""Tests G9 — GET /api/analysis/seasonality (saisonnalité par catégorie).

Couvre :
1. Catégorie avec 4 mois de données → has_enough_data=False, months_available=4
2. Catégorie inconnue → points=[]
3. Catégorie avec 13+ mois → has_enough_data=True
4. READER sans accès → 403
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.category import Category
from app.models.entity import Entity
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction, TransactionCategorizationSource
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mk_entity(db: Session, name: str = "G9 Entity") -> Entity:
    e = Entity(name=name, legal_name=name)
    db.add(e)
    db.flush()
    return e


def _mk_bank_account(db: Session, entity_id: int, suffix: str = "g9") -> BankAccount:
    ba = BankAccount(
        entity_id=entity_id,
        bank_code="delubac",
        bank_name="Delubac",
        iban=f"FR760000000000000000000{suffix}",
        name=f"Compte G9 {suffix}",
    )
    db.add(ba)
    db.flush()
    return ba


def _mk_category(db: Session, name: str = "Loyer G9", slug: str = "loyer-g9") -> Category:
    cat = Category(name=name, slug=slug, is_system=False)
    db.add(cat)
    db.flush()
    return cat


def _mk_tx_for_month(
    db: Session,
    bank_account_id: int,
    year: int,
    month: int,
    category_id: int,
    amount: Decimal,
    row_idx: int,
) -> None:
    """Crée un import + une transaction pour le mois/année donnés."""
    period_end = date(year, month, 28)
    ir = ImportRecord(
        bank_account_id=bank_account_id,
        bank_code="delubac",
        status=ImportStatus.COMPLETED,
        period_start=period_end.replace(day=1),
        period_end=period_end,
        opening_balance=Decimal("0"),
        closing_balance=Decimal("1000"),
        imported_count=1,
    )
    db.add(ir)
    db.flush()

    tx = Transaction(
        bank_account_id=bank_account_id,
        import_id=ir.id,
        operation_date=period_end,
        value_date=period_end,
        amount=amount,
        label=f"tx-g9-{year}-{month}-{row_idx}",
        raw_label=f"tx-g9-{year}-{month}",
        dedup_key=f"dk-g9-{bank_account_id}-{year}-{month}-{row_idx}",
        statement_row_index=row_idx,
        is_aggregation_parent=False,
        normalized_label=f"tx-g9-{year}-{month}",
        categorized_by=TransactionCategorizationSource.NONE,
        category_id=category_id,
    )
    db.add(tx)


# ---------------------------------------------------------------------------
# Test 1 : 4 mois de données → has_enough_data=False
# ---------------------------------------------------------------------------


def test_seasonality_insufficient_data(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """4 mois de données → has_enough_data=False, months_available=4."""
    entity = _mk_entity(db_session, "G9 Insufficient Entity")
    ba = _mk_bank_account(db_session, entity.id, "g9a")
    cat = _mk_category(db_session, "Loyer Saisonnalite", "loyer-saisonnalite")
    db_session.commit()

    today = date.today()
    # Créer 4 mois de transactions
    for months_back in range(4):
        year = today.year
        month = today.month - months_back
        if month <= 0:
            month += 12
            year -= 1
        _mk_tx_for_month(
            db_session, ba.id, year, month, cat.id, Decimal("-500"), row_idx=months_back
        )
    db_session.commit()

    resp = client.get(
        f"/api/analysis/seasonality?entity_id={entity.id}&category_id={cat.id}"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_enough_data"] is False
    assert data["months_available"] == 4
    assert len(data["points"]) == 4
    assert data["entity_id"] == entity.id
    assert data["category_id"] == cat.id


# ---------------------------------------------------------------------------
# Test 2 : catégorie inconnue → points=[]
# ---------------------------------------------------------------------------


def test_seasonality_unknown_category(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """Catégorie inconnue (99999) → points=[], months_available=0."""
    entity = _mk_entity(db_session, "G9 Unknown Cat Entity")
    _mk_bank_account(db_session, entity.id, "g9b")
    db_session.commit()

    resp = client.get(
        f"/api/analysis/seasonality?entity_id={entity.id}&category_id=99999"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["points"] == []
    assert data["months_available"] == 0
    assert data["has_enough_data"] is False


# ---------------------------------------------------------------------------
# Test 3 : 13+ mois → has_enough_data=True, points triés chronologiquement
# ---------------------------------------------------------------------------


def test_seasonality_enough_data(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """13 mois de données → has_enough_data=True, points triés chronologiquement."""
    entity = _mk_entity(db_session, "G9 Full Data Entity")
    ba = _mk_bank_account(db_session, entity.id, "g9c")
    cat = _mk_category(db_session, "Telecom G9", "telecom-g9")
    db_session.commit()

    today = date.today()
    # Créer 13 mois de transactions
    for months_back in range(13):
        year = today.year
        month = today.month - months_back
        while month <= 0:
            month += 12
            year -= 1
        _mk_tx_for_month(
            db_session, ba.id, year, month, cat.id, Decimal("-200"), row_idx=100 + months_back
        )
    db_session.commit()

    resp = client.get(
        f"/api/analysis/seasonality?entity_id={entity.id}&category_id={cat.id}"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_enough_data"] is True
    assert data["months_available"] == 13
    assert len(data["points"]) == 13
    # Vérifier que les points sont triés chronologiquement (month croissant)
    months = [p["month"] for p in data["points"]]
    assert months == sorted(months)


# ---------------------------------------------------------------------------
# Test 4 : READER sans accès → 403
# ---------------------------------------------------------------------------


def test_seasonality_access_denied(
    client: TestClient,
    auth_user_reader: User,
    db_session: Session,
) -> None:
    """READER sans accès à l'entité → 403."""
    entity = _mk_entity(db_session, "G9 Foreign Entity")
    cat = _mk_category(db_session, "Cat G9 Foreign", "cat-g9-foreign")
    db_session.commit()

    resp = client.get(
        f"/api/analysis/seasonality?entity_id={entity.id}&category_id={cat.id}"
    )
    assert resp.status_code == 403
