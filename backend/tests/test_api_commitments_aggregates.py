"""GET /api/commitments/aggregates retourne les KPI consolidés par direction."""
from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.commitment import Commitment, CommitmentDirection, CommitmentStatus


def _commit(
    entity_id: int,
    direction: CommitmentDirection,
    amount_cents: int,
    expected_offset_days: int,
    status: CommitmentStatus = CommitmentStatus.PENDING,
) -> Commitment:
    today = date.today()
    return Commitment(
        entity_id=entity_id,
        direction=direction,
        amount_cents=amount_cents,
        issue_date=today - timedelta(days=30),
        expected_date=today + timedelta(days=expected_offset_days),
        status=status,
    )


def test_aggregates_kpi_per_direction(
    client: TestClient,
    db_session: Session,
    auth_user_with_bank_account,
) -> None:
    e_id = auth_user_with_bank_account["bank_account"].entity_id
    db_session.add_all([
        # in : 1 dans 15j (10€), 1 retard 3j (20€), 1 fantôme retard 14j (50€)
        _commit(e_id, CommitmentDirection.IN, 1000, 15),
        _commit(e_id, CommitmentDirection.IN, 2000, -3),
        _commit(e_id, CommitmentDirection.IN, 5000, -14),
        # out : 1 dans 7j (40€)
        _commit(e_id, CommitmentDirection.OUT, 4000, 7),
        # cancelled : ignoré
        _commit(e_id, CommitmentDirection.IN, 9999, -10, status=CommitmentStatus.CANCELLED),
    ])
    db_session.commit()

    resp = client.get("/api/commitments/aggregates", params={"entity_id": e_id})
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["in"]["total_30d_cents"] == 1000
    assert body["in"]["overdue_total_cents"] == 2000 + 5000
    assert body["in"]["overdue_count"] == 2
    assert body["in"]["phantom_count"] == 1

    assert body["out"]["total_30d_cents"] == 4000
    assert body["out"]["overdue_count"] == 0
    assert body["out"]["phantom_count"] == 0


def test_aggregates_filtered_by_direction(
    client: TestClient,
    db_session: Session,
    auth_user_with_bank_account,
) -> None:
    e_id = auth_user_with_bank_account["bank_account"].entity_id
    db_session.add(_commit(e_id, CommitmentDirection.IN, 1000, 5))
    db_session.add(_commit(e_id, CommitmentDirection.OUT, 2000, 5))
    db_session.commit()

    resp = client.get(
        "/api/commitments/aggregates",
        params={"entity_id": e_id, "direction": "in"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["in"]["total_30d_cents"] == 1000
    assert body.get("out") is None
