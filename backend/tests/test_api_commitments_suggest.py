"""GET /api/commitments/{id}/suggest-matches expose score + breakdown."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.commitment import Commitment, CommitmentDirection, CommitmentStatus
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction


def test_suggest_matches_exposes_score_and_breakdown(
    client: TestClient,
    db_session: Session,
    auth_user_with_bank_account,
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    e_id = ba.entity_id
    today = date.today()

    imp = ImportRecord(
        bank_account_id=ba.id,
        bank_code="delubac",
        status=ImportStatus.COMPLETED,
    )
    db_session.add(imp)
    db_session.flush()

    c = Commitment(
        entity_id=e_id,
        direction=CommitmentDirection.OUT,
        amount_cents=10000,
        issue_date=today - timedelta(days=10),
        expected_date=today,
        status=CommitmentStatus.PENDING,
    )
    db_session.add(c)
    db_session.flush()

    db_session.add(Transaction(
        bank_account_id=ba.id,
        import_id=imp.id,
        operation_date=today,
        value_date=today,
        label="ACME 100",
        raw_label="ACME 100",
        normalized_label="acme 100",
        amount=Decimal("-100"),
        dedup_key="dks1",
        statement_row_index=1,
    ))
    db_session.commit()

    resp = client.get(f"/api/commitments/{c.id}/suggest-matches")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["candidates"]) == 1
    cand = body["candidates"][0]
    assert cand["score"] is not None
    assert cand["score_breakdown"]["date_diff_days"] == 0
    assert cand["score_breakdown"]["amount_diff_eur"] == 0.0
    assert cand["score_breakdown"]["counterparty_match"] is False
