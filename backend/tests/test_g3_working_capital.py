"""Tests G3 — GET /api/analysis/working-capital (endpoint existant, validé G3).

G3 est un branchement UI uniquement. Ce fichier vérifie que l'endpoint
existant répond correctement et que has_data=False quand il n'y a pas
d'engagements matchés à des transactions.
"""
from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Commitment, CommitmentDirection, CommitmentStatus


class TestWorkingCapitalEndpoint:
    def test_returns_200_with_entity(
        self,
        client: TestClient,
        auth_user_with_bank_account: dict,
    ) -> None:
        """L'endpoint /api/analysis/working-capital doit répondre 200."""
        entity = auth_user_with_bank_account["entity"]
        resp = client.get(
            "/api/analysis/working-capital",
            params={"entity_id": entity.id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "dso_days" in data
        assert "dpo_days" in data
        assert "bfr_cents" in data
        assert "has_data" in data

    def test_no_commitments_has_data_false(
        self,
        client: TestClient,
        auth_user_with_bank_account: dict,
    ) -> None:
        """Sans engagements matchés, has_data doit être False."""
        entity = auth_user_with_bank_account["entity"]
        resp = client.get(
            "/api/analysis/working-capital",
            params={"entity_id": entity.id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_data"] is False
        assert data["dso_days"] is None
        assert data["dpo_days"] is None

    def test_only_cancelled_commitments_has_data_false(
        self,
        client: TestClient,
        db_session: Session,
        auth_user_with_bank_account: dict,
    ) -> None:
        """Engagements uniquement annulés -> has_data=False (état vide UI).

        Regression : un commitment `cancelled` solo ne doit pas faire passer
        has_data=True, sinon l'UI affiche BFR=0 et DSO=DPO=— au lieu du CTA
        "Aller aux Engagements".
        """
        entity = auth_user_with_bank_account["entity"]
        today = date.today()
        db_session.add(
            Commitment(
                entity_id=entity.id,
                direction=CommitmentDirection.OUT,
                amount_cents=10000,
                issue_date=today - timedelta(days=30),
                expected_date=today + timedelta(days=5),
                status=CommitmentStatus.CANCELLED,
            )
        )
        db_session.commit()

        resp = client.get(
            "/api/analysis/working-capital",
            params={"entity_id": entity.id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_data"] is False, (
            "1 commitment annulé seul ne doit pas activer has_data"
        )

    def test_access_denied_foreign_entity(
        self,
        client: TestClient,
        auth_user_reader: object,
        other_entity_bank_account,
    ) -> None:
        """Un READER sans accès à l'entité doit obtenir 403."""
        other_entity_id = other_entity_bank_account.entity_id
        resp = client.get(
            "/api/analysis/working-capital",
            params={"entity_id": other_entity_id},
        )
        assert resp.status_code == 403
