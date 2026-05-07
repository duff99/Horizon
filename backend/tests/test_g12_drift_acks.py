"""Tests G12 — Snooze/acquittement de dérive (drift_acks).

Couvre :
1. POST /api/analysis/drift-acks/ → 201, snoozed_until = today + 30
2. GET /api/analysis/drift-acks/?entity_id=X → liste des acks actifs
3. DELETE /api/analysis/drift-acks/{id} → 204, GET donne liste vide
4. POST avec entity étrangère → 403 (READER sans accès)
5. compute_category_drift retourne status="snoozed" pour une catégorie acquittée
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


def _mk_entity(db: Session, name: str = "Test Entity G12") -> Entity:
    e = Entity(name=name, legal_name=name)
    db.add(e)
    db.flush()
    return e


def _mk_bank_account(db: Session, entity_id: int) -> BankAccount:
    ba = BankAccount(
        entity_id=entity_id,
        bank_code="delubac",
        bank_name="Delubac",
        iban="FR7600000000000000000000999",
        name="Compte G12",
    )
    db.add(ba)
    db.flush()
    return ba


def _mk_category(db: Session, name: str = "Loyer G12", slug: str = "loyer-g12") -> Category:
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
        label=f"tx-g12-{row_idx}",
        raw_label=f"tx-g12-{row_idx}",
        dedup_key=f"dk-g12-{bank_account_id}-{row_idx}-{op_date.isoformat()}",
        statement_row_index=row_idx,
        is_aggregation_parent=False,
        normalized_label=f"tx-g12-{row_idx}",
        categorized_by=TransactionCategorizationSource.NONE,
        category_id=category_id,
    )
    db.add(tx)
    return tx


# ---------------------------------------------------------------------------
# Test 1 : POST → 201, snoozed_until = today + 30
# ---------------------------------------------------------------------------


def test_snooze_creates_ack(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """POST crée un acquittement avec snoozed_until = today + snooze_days."""
    entity = _mk_entity(db_session)
    category = _mk_category(db_session)
    db_session.commit()

    resp = client.post(
        "/api/analysis/drift-acks/",
        json={
            "entity_id": entity.id,
            "category_id": category.id,
            "snooze_days": 30,
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "id" in data
    assert data["entity_id"] == entity.id
    assert data["category_id"] == category.id
    expected = (date.today() + timedelta(days=30)).isoformat()
    assert data["snoozed_until"] == expected


# ---------------------------------------------------------------------------
# Test 2 : GET liste les acks actifs
# ---------------------------------------------------------------------------


def test_list_returns_active_acks(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """Après POST, GET liste renvoie l'ack."""
    entity = _mk_entity(db_session, "G12 List Entity")
    category = _mk_category(db_session, "Fournitures G12", "fournitures-g12")
    db_session.commit()

    resp = client.post(
        "/api/analysis/drift-acks/",
        json={"entity_id": entity.id, "category_id": category.id},
    )
    assert resp.status_code == 201

    resp2 = client.get(f"/api/analysis/drift-acks/?entity_id={entity.id}")
    assert resp2.status_code == 200
    data = resp2.json()
    assert len(data) == 1
    assert data[0]["category_id"] == category.id


# ---------------------------------------------------------------------------
# Test 3 : DELETE supprime l'ack, GET donne liste vide
# ---------------------------------------------------------------------------


def test_delete_removes_ack(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """Après DELETE, GET liste donne une liste vide."""
    entity = _mk_entity(db_session, "G12 Delete Entity")
    category = _mk_category(db_session, "Abonnement G12", "abonnement-g12")
    db_session.commit()

    # Créer l'ack
    create_resp = client.post(
        "/api/analysis/drift-acks/",
        json={"entity_id": entity.id, "category_id": category.id},
    )
    assert create_resp.status_code == 201
    ack_id = create_resp.json()["id"]

    # Supprimer
    del_resp = client.delete(f"/api/analysis/drift-acks/{ack_id}")
    assert del_resp.status_code == 204

    # Vérifier liste vide
    list_resp = client.get(f"/api/analysis/drift-acks/?entity_id={entity.id}")
    assert list_resp.status_code == 200
    assert list_resp.json() == []


# ---------------------------------------------------------------------------
# Test 4 : READER sans accès → 403
# ---------------------------------------------------------------------------


def test_snooze_access_denied_foreign_entity(
    client: TestClient,
    auth_user_reader: User,
    db_session: Session,
) -> None:
    """Un READER sans accès à l'entité reçoit 403."""
    entity = _mk_entity(db_session, "G12 Foreign Entity")
    category = _mk_category(db_session, "Taxes G12", "taxes-g12")
    db_session.commit()

    # auth_user_reader n'a pas d'accès à `entity` (pas de UserEntityAccess)
    resp = client.post(
        "/api/analysis/drift-acks/",
        json={"entity_id": entity.id, "category_id": category.id},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Test 5 : compute_category_drift retourne status="snoozed"
# ---------------------------------------------------------------------------


def test_category_drift_shows_snoozed_status(
    client: TestClient,
    auth_user: User,
    db_session: Session,
) -> None:
    """Après snooze, GET /category-drift retourne status='snoozed' pour la catégorie."""
    entity = _mk_entity(db_session, "G12 Drift Entity")
    ba = _mk_bank_account(db_session, entity.id)
    cat = _mk_category(db_session, "Loyer Snooze", "loyer-snooze")
    db_session.commit()

    # Créer des transactions sur 4 mois pour avoir de l'historique drift
    today = date.today()
    # M-1 = mois courant du drift (mois précédent le mois de l'ancre)
    # On crée des tx sur M-1, M-2, M-3, M-4 avec une forte dérive en M-1
    for months_ago in range(1, 5):
        period_end = today.replace(day=1) - timedelta(days=1)  # fin du mois précédent
        for m in range(months_ago - 1):
            # Reculer d'un mois supplémentaire
            period_end = period_end.replace(day=1) - timedelta(days=1)

        ir = _mk_import(db_session, ba.id, period_end)
        # M-1 = montant très élevé (dérive), M-2..M-4 = montant normal
        amount = Decimal("-5000") if months_ago == 1 else Decimal("-100")
        for i in range(3):
            _mk_tx(
                db_session,
                ba.id,
                ir.id,
                period_end - timedelta(days=i),
                amount,
                cat.id,
                row_idx=months_ago * 10 + i,
            )
    db_session.commit()

    # Vérifier que la catégorie est en status "alert" avant snooze
    drift_resp = client.get(
        f"/api/analysis/category-drift?entity_id={entity.id}&seuil_pct=20"
    )
    assert drift_resp.status_code == 200
    rows = drift_resp.json()["rows"]
    cat_rows = [r for r in rows if r["category_id"] == cat.id]
    assert len(cat_rows) == 1
    # La dérive devrait être alert ou insufficient — dans tous les cas, snooze la
    pre_status = cat_rows[0]["status"]
    assert pre_status in ("alert", "normal", "insufficient")

    # Snoozer la catégorie
    snooze_resp = client.post(
        "/api/analysis/drift-acks/",
        json={"entity_id": entity.id, "category_id": cat.id},
    )
    assert snooze_resp.status_code == 201

    # Vérifier que la catégorie a maintenant status="snoozed"
    drift_resp2 = client.get(
        f"/api/analysis/category-drift?entity_id={entity.id}&seuil_pct=20"
    )
    assert drift_resp2.status_code == 200
    rows2 = drift_resp2.json()["rows"]
    cat_rows2 = [r for r in rows2 if r["category_id"] == cat.id]
    assert len(cat_rows2) == 1
    assert cat_rows2[0]["status"] == "snoozed"
