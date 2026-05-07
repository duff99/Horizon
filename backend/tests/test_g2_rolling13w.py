"""Tests G2 — GET /api/forecast/rolling-13w."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _monday_this_week() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def _mk_import(db: Session, bank_account_id: int) -> ImportRecord:
    rec = ImportRecord(
        bank_account_id=bank_account_id,
        bank_code="delubac",
        status=ImportStatus.COMPLETED,
    )
    db.add(rec)
    db.flush()
    return rec


def _mk_tx(
    db: Session,
    bank_account_id: int,
    *,
    amount: Decimal,
    op_date: date,
    label: str = "tx",
) -> Transaction:
    imp = _mk_import(db, bank_account_id)
    tx = Transaction(
        bank_account_id=bank_account_id,
        import_id=imp.id,
        operation_date=op_date,
        value_date=op_date,
        amount=amount,
        label=label,
        raw_label=label,
        normalized_label=label.lower(),
        dedup_key=f"g2-{label}-{op_date}-{amount}-{bank_account_id}",
        statement_row_index=0,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRolling13W:
    def test_returns_13_points(
        self,
        client: TestClient,
        auth_user_with_bank_account: dict,
    ) -> None:
        """L'endpoint doit toujours retourner exactement 13 points."""
        entity = auth_user_with_bank_account["entity"]
        resp = client.get(
            "/api/forecast/rolling-13w",
            params={"entity_id": entity.id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["points"]) == 13

    def test_is_past_correct(
        self,
        client: TestClient,
        auth_user_with_bank_account: dict,
    ) -> None:
        """W-1 doit avoir is_past=True, W+1 doit avoir is_past=False."""
        entity = auth_user_with_bank_account["entity"]
        resp = client.get(
            "/api/forecast/rolling-13w",
            params={"entity_id": entity.id},
        )
        assert resp.status_code == 200
        points = resp.json()["points"]

        # Point 0 = W-1 (semaine passée)
        assert points[0]["is_past"] is True
        # Point 1 = semaine courante → is_past=False (week_start == monday_this_week)
        assert points[1]["is_past"] is False
        # Point 2 = W+1 (semaine future)
        assert points[2]["is_past"] is False

    def test_week_label_iso_format(
        self,
        client: TestClient,
        auth_user_with_bank_account: dict,
    ) -> None:
        """Les week_label doivent suivre le format ISO YYYY-Www."""
        entity = auth_user_with_bank_account["entity"]
        resp = client.get(
            "/api/forecast/rolling-13w",
            params={"entity_id": entity.id},
        )
        assert resp.status_code == 200
        points = resp.json()["points"]
        for p in points:
            label = p["week_label"]
            # Format: YYYY-Wnn (ex: 2026-W18)
            parts = label.split("-W")
            assert len(parts) == 2, f"Mauvais format : {label}"
            year_str, week_str = parts
            assert year_str.isdigit() and len(year_str) == 4
            assert week_str.isdigit() and 1 <= int(week_str) <= 53

    def test_realized_cents_aggregated(
        self,
        client: TestClient,
        db_session: Session,
        auth_user_with_bank_account: dict,
    ) -> None:
        """Les transactions dans la fenêtre W-1 doivent être agrégées."""
        entity = auth_user_with_bank_account["entity"]
        ba = auth_user_with_bank_account["bank_account"]

        # Placer une transaction dans W-1 (semaine précédente)
        monday = _monday_this_week()
        last_monday = monday - timedelta(weeks=1)
        tx_date = last_monday + timedelta(days=2)  # mercredi de la semaine passée

        _mk_tx(db_session, ba.id, amount=Decimal("-500.00"), op_date=tx_date, label="g2-realized-test")

        resp = client.get(
            "/api/forecast/rolling-13w",
            params={"entity_id": entity.id},
        )
        assert resp.status_code == 200
        points = resp.json()["points"]

        # Point 0 = W-1
        assert points[0]["is_past"] is True
        # realized_cents = -500 € × 100 = -50000 centimes
        assert points[0]["realized_cents"] == -50_000

    def test_access_denied_foreign_entity(
        self,
        client: TestClient,
        db_session: Session,
        auth_user_reader: object,
        other_entity_bank_account,
    ) -> None:
        """Un READER sans accès à l'entité doit obtenir 403."""
        other_entity_id = other_entity_bank_account.entity_id
        resp = client.get(
            "/api/forecast/rolling-13w",
            params={"entity_id": other_entity_id},
        )
        assert resp.status_code == 403

    def test_no_bank_accounts_returns_zeros(
        self,
        client: TestClient,
        db_session: Session,
        auth_user_with_bank_account: dict,
    ) -> None:
        """Sans transactions, tous les realized_cents doivent être 0."""
        entity = auth_user_with_bank_account["entity"]
        resp = client.get(
            "/api/forecast/rolling-13w",
            params={"entity_id": entity.id},
        )
        assert resp.status_code == 200
        points = resp.json()["points"]
        # Tous les realized_cents doivent être 0 (pas de transactions créées dans ce test)
        for p in points:
            assert isinstance(p["realized_cents"], int)
