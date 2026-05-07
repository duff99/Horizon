"""Tests G4 — GET /api/analysis/anomalies (détection p95).

Couvre :
1. Entité sans import → anomaly_count=0, rows=[]
2. Transaction à 10x le montant habituel → apparaît dans les anomalies
3. Catégorie avec < 5 transactions → ignorée (pas de p95 calculé)
4. Accès refusé si READER sans accès à l'entité → 403
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
from app.models.user_entity_access import UserEntityAccess


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mk_entity(db: Session, name: str = "G4 Entity") -> Entity:
    e = Entity(name=name, legal_name=name)
    db.add(e)
    db.flush()
    return e


def _mk_bank_account(db: Session, entity_id: int, iban_suffix: str = "001") -> BankAccount:
    ba = BankAccount(
        entity_id=entity_id,
        bank_code="delubac",
        bank_name="Delubac",
        iban=f"FR76000000000000000000{iban_suffix}",
        name=f"Compte G4 {iban_suffix}",
    )
    db.add(ba)
    db.flush()
    return ba


def _mk_category(db: Session, name: str = "Loyer G4", slug: str = "loyer-g4") -> Category:
    cat = Category(name=name, slug=slug, is_system=False)
    db.add(cat)
    db.flush()
    return cat


def _mk_import(db: Session, bank_account_id: int, period_end: date) -> ImportRecord:
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
    return ir


def _mk_tx(
    db: Session,
    bank_account_id: int,
    import_id: int,
    op_date: date,
    amount: Decimal,
    category_id: int | None,
    row_idx: int,
) -> Transaction:
    tx = Transaction(
        bank_account_id=bank_account_id,
        import_id=import_id,
        operation_date=op_date,
        value_date=op_date,
        amount=amount,
        label=f"tx-g4-{row_idx}",
        raw_label=f"tx-g4-{row_idx}",
        dedup_key=f"dk-g4-{bank_account_id}-{row_idx}-{op_date.isoformat()}",
        statement_row_index=row_idx,
        is_aggregation_parent=False,
        normalized_label=f"tx-g4-{row_idx}",
        categorized_by=TransactionCategorizationSource.NONE,
        category_id=category_id,
    )
    db.add(tx)
    return tx


# ---------------------------------------------------------------------------
# Test 1 : entité sans import → rows=[]
# ---------------------------------------------------------------------------


def test_anomalies_empty_no_import(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """Entité avec un compte bancaire mais aucun import → rows=[]."""
    entity = _mk_entity(db_session, "G4 Empty Entity")
    _mk_bank_account(db_session, entity.id, "100")
    db_session.commit()

    resp = client.get(f"/api/analysis/anomalies?entity_id={entity.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["anomaly_count"] == 0
    assert data["rows"] == []


# ---------------------------------------------------------------------------
# Test 2 : transaction à montant × 10 → détectée comme anomalie
# ---------------------------------------------------------------------------


def test_anomalies_detects_high_amount(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """Une transaction à 10× le montant habituel apparaît dans les anomalies."""
    entity = _mk_entity(db_session, "G4 Anomaly Entity")
    ba = _mk_bank_account(db_session, entity.id, "200")
    cat = _mk_category(db_session, "Fournitures G4", "fournitures-g4")
    db_session.commit()

    today = date.today()
    # Créer 10 transactions "normales" de -100€ sur les 180 derniers jours
    for i in range(10):
        op_date = today - timedelta(days=60 + i * 10)
        ir = _mk_import(db_session, ba.id, op_date)
        _mk_tx(db_session, ba.id, ir.id, op_date, Decimal("-100"), cat.id, row_idx=i)

    # Créer 1 transaction très élevée (-2000€) dans les 30 derniers jours
    recent_date = today - timedelta(days=10)
    ir_recent = _mk_import(db_session, ba.id, recent_date)
    _mk_tx(
        db_session, ba.id, ir_recent.id, recent_date, Decimal("-2000"), cat.id, row_idx=100
    )
    db_session.commit()

    resp = client.get(f"/api/analysis/anomalies?entity_id={entity.id}&days=180")
    assert resp.status_code == 200
    data = resp.json()
    assert data["anomaly_count"] >= 1
    # La transaction à -2000€ doit apparaître
    tx_ids = [r["transaction_id"] for r in data["rows"]]
    amounts = [r["amount_cents"] for r in data["rows"]]
    # Le montant de -2000€ = -200000 centimes
    assert any(abs(a) == 200000 for a in amounts)
    # ratio doit être significatif (> 1)
    assert all(r["ratio"] > 1 for r in data["rows"])


# ---------------------------------------------------------------------------
# Test 3 : catégorie avec < 5 transactions → ignorée
# ---------------------------------------------------------------------------


def test_anomalies_ignores_sparse_categories(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """Une catégorie avec < 5 transactions n'est pas analysée (p95 non fiable)."""
    entity = _mk_entity(db_session, "G4 Sparse Entity")
    ba = _mk_bank_account(db_session, entity.id, "300")
    cat = _mk_category(db_session, "Cat Rare G4", "cat-rare-g4")
    db_session.commit()

    today = date.today()
    # Créer seulement 3 transactions (< 5 = seuil MIN_TX_FOR_P95)
    for i in range(3):
        op_date = today - timedelta(days=5 + i)
        ir = _mk_import(db_session, ba.id, op_date)
        _mk_tx(
            db_session, ba.id, ir.id, op_date, Decimal("-10000"), cat.id, row_idx=200 + i
        )
    db_session.commit()

    resp = client.get(f"/api/analysis/anomalies?entity_id={entity.id}&days=180")
    assert resp.status_code == 200
    data = resp.json()
    # La catégorie avec < 5 tx ne doit pas générer d'anomalies
    cat_ids_in_result = [r["category_id"] for r in data["rows"]]
    assert cat.id not in cat_ids_in_result


# ---------------------------------------------------------------------------
# Test 4 : READER sans accès → 403
# ---------------------------------------------------------------------------


def test_anomalies_access_denied_foreign_entity(
    client: TestClient,
    auth_user_reader: User,
    db_session: Session,
) -> None:
    """Un READER sans accès à l'entité reçoit 403."""
    entity = _mk_entity(db_session, "G4 Foreign Entity")
    db_session.commit()

    resp = client.get(f"/api/analysis/anomalies?entity_id={entity.id}")
    assert resp.status_code == 403
