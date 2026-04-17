"""GET /api/transactions?uncategorized=true + POST /api/transactions/bulk-categorize."""
from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient

from app.models.category import Category
from app.models.transaction import Transaction, TransactionCategorizationSource
from app.models.import_record import ImportRecord, ImportStatus
from app.models.user_entity_access import UserEntityAccess


def _grant_access(db_session, user, bank_account) -> None:
    exists = db_session.query(UserEntityAccess).filter_by(
        user_id=user.id, entity_id=bank_account.entity_id,
    ).first()
    if exists:
        return
    db_session.add(UserEntityAccess(user_id=user.id, entity_id=bank_account.entity_id))
    db_session.commit()


def _mk_txs(db_session, bank_account, count: int = 2) -> list[int]:
    imp = ImportRecord(
        bank_account_id=bank_account.id, filename="b.pdf",
        file_sha256="q"*64, bank_code="DELUBAC", status=ImportStatus.COMPLETED,
    )
    db_session.add(imp); db_session.commit()
    ids = []
    for i in range(count):
        t = Transaction(
            bank_account_id=bank_account.id, import_id=imp.id,
            operation_date=date(2026, 2, i + 1), value_date=date(2026, 2, i + 1),
            amount=Decimal("-5"), label=f"X{i}", raw_label=f"X{i}",
            normalized_label=f"X{i}",
            dedup_key=f"bt-{i}-" + "q"*58, statement_row_index=i,
        )
        db_session.add(t); db_session.commit()
        ids.append(t.id)
    return ids


def test_list_uncategorized_filter(
    client: TestClient, auth_user, db_session, bank_account,
) -> None:
    _grant_access(db_session, auth_user, bank_account)
    ids = _mk_txs(db_session, bank_account, count=2)
    cat = Category(name="c", slug="c-api-bulk1", is_system=False)
    db_session.add(cat); db_session.commit()
    t = db_session.get(Transaction, ids[0])
    t.category_id = cat.id
    t.categorized_by = TransactionCategorizationSource.MANUAL
    db_session.commit()

    r = client.get("/api/transactions?uncategorized=true")
    assert r.status_code == 200
    rows = r.json().get("items", r.json())
    returned_ids = {row["id"] for row in rows}
    assert ids[0] not in returned_ids
    assert ids[1] in returned_ids


def test_bulk_categorize_sets_manual(
    client: TestClient, auth_user, db_session, bank_account,
) -> None:
    _grant_access(db_session, auth_user, bank_account)
    ids = _mk_txs(db_session, bank_account, count=3)
    cat = Category(name="c", slug="c-api-bulk2", is_system=False)
    db_session.add(cat); db_session.commit()

    r = client.post("/api/transactions/bulk-categorize", json={
        "transaction_ids": ids,
        "category_id": cat.id,
    })
    assert r.status_code == 200, r.text
    for tid in ids:
        t = db_session.get(Transaction, tid)
        db_session.refresh(t)
        assert t.category_id == cat.id
        assert t.categorized_by == TransactionCategorizationSource.MANUAL


def test_bulk_categorize_requires_editor(
    client: TestClient, auth_user_reader, db_session, bank_account,
) -> None:
    _grant_access(db_session, auth_user_reader, bank_account)
    ids = _mk_txs(db_session, bank_account, count=1)
    cat = Category(name="c", slug="c-api-bulk3", is_system=False)
    db_session.add(cat); db_session.commit()
    r = client.post("/api/transactions/bulk-categorize", json={
        "transaction_ids": ids, "category_id": cat.id,
    })
    assert r.status_code == 403
