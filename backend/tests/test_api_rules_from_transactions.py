"""POST /api/rules/from-transactions."""
from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient

from app.models.transaction import Transaction
from app.models.import_record import ImportRecord, ImportStatus


def test_suggest_rule_from_common_substring(
    client: TestClient, auth_user, db_session, bank_account,
) -> None:
    imp = ImportRecord(
        bank_account_id=bank_account.id, filename="s.pdf",
        file_sha256="s"*64, bank_code="DELUBAC", status=ImportStatus.COMPLETED,
    )
    db_session.add(imp); db_session.commit()
    t1 = Transaction(
        bank_account_id=bank_account.id, import_id=imp.id,
        operation_date=date(2026, 1, 1), value_date=date(2026, 1, 1),
        amount=Decimal("-50"), label="PRLV URSSAF REF 111",
        raw_label="PRLV URSSAF REF 111",
        normalized_label="PRLV URSSAF REF 111",
        dedup_key="sg-1-" + "s"*58, statement_row_index=0,
    )
    t2 = Transaction(
        bank_account_id=bank_account.id, import_id=imp.id,
        operation_date=date(2026, 1, 2), value_date=date(2026, 1, 2),
        amount=Decimal("-50"), label="PRLV URSSAF REF 222",
        raw_label="PRLV URSSAF REF 222",
        normalized_label="PRLV URSSAF REF 222",
        dedup_key="sg-2-" + "s"*58, statement_row_index=1,
    )
    db_session.add_all([t1, t2]); db_session.commit()

    r = client.post("/api/rules/from-transactions", json={
        "transaction_ids": [t1.id, t2.id],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert "URSSAF" in body["suggested_label_value"]
    assert body["transaction_count"] == 2
