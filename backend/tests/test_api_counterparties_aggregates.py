"""GET /api/counterparties retourne les agrégats par tiers."""
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.commitment import Commitment, CommitmentDirection, CommitmentStatus
from app.models.counterparty import Counterparty, CounterpartyStatus
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction


def test_list_counterparties_returns_aggregates(
    client: TestClient,
    db_session: Session,
    auth_user_with_bank_account,
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    entity_id = ba.entity_id

    cp = Counterparty(
        entity_id=entity_id, name="ACME", normalized_name="ACME",
        status=CounterpartyStatus.ACTIVE,
    )
    imp = ImportRecord(
        bank_account_id=ba.id, filename="p.pdf",
        file_sha256="a" * 64, bank_code="DELUBAC", status=ImportStatus.COMPLETED,
    )
    db_session.add_all([cp, imp])
    db_session.flush()

    db_session.add_all([
        Transaction(
            bank_account_id=ba.id, import_id=imp.id,
            counterparty_id=cp.id,
            operation_date=date(2026, 4, 1), value_date=date(2026, 4, 1),
            label="X", raw_label="X", amount=Decimal("100"),
            dedup_key="dk1", statement_row_index=1,
        ),
        Transaction(
            bank_account_id=ba.id, import_id=imp.id,
            counterparty_id=cp.id,
            operation_date=date(2026, 4, 15), value_date=date(2026, 4, 15),
            label="Y", raw_label="Y", amount=Decimal("-50"),
            dedup_key="dk2", statement_row_index=2,
        ),
    ])
    db_session.add(Commitment(
        entity_id=entity_id, counterparty_id=cp.id,
        direction=CommitmentDirection.IN,
        amount_cents=20000,
        issue_date=date(2026, 4, 1),
        expected_date=date(2026, 5, 1),
        status=CommitmentStatus.PENDING,
    ))
    db_session.commit()

    resp = client.get("/api/counterparties", params={"entity_id": entity_id})
    assert resp.status_code == 200
    body = resp.json()
    row = next(r for r in body if r["id"] == cp.id)
    assert row["transaction_count"] == 2
    assert row["volume_cumulated"] == 150.0
    assert row["last_operation_date"] is not None
    assert row["pending_commitment_count"] == 1
