"""POST /api/rules/preview."""
from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient

from app.models.category import Category
from app.models.transaction import Transaction
from app.models.import_record import ImportRecord, ImportStatus


def _cat(db_session) -> Category:
    c = Category(name="c", slug="c-api-preview", is_system=False)
    db_session.add(c); db_session.commit()
    return c


def test_preview_returns_count_and_sample(
    client: TestClient, auth_user, db_session, bank_account,
) -> None:
    cat = _cat(db_session)
    imp = ImportRecord(
        bank_account_id=bank_account.id, filename="p.pdf",
        file_sha256="e"*64, bank_code="DELUBAC", status=ImportStatus.COMPLETED,
    )
    db_session.add(imp); db_session.commit()
    for i in range(3):
        db_session.add(Transaction(
            bank_account_id=bank_account.id, import_id=imp.id,
            operation_date=date(2026, 1, i + 1), value_date=date(2026, 1, i + 1),
            amount=Decimal("-10"), label=f"URSSAF {i}", raw_label=f"URSSAF {i}",
            normalized_label=f"URSSAF {i}",
            dedup_key=f"pv-{i}-" + "e"*58, statement_row_index=i,
        ))
    db_session.commit()

    r = client.post("/api/rules/preview", json={
        "name": "Preview", "priority": 7500,
        "label_operator": "CONTAINS", "label_value": "URSSAF",
        "direction": "ANY", "category_id": cat.id,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["matching_count"] == 3
    assert len(body["sample"]) == 3
