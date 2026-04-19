"""E2E Plan 2 : import auto-catégorisation + règle custom + preview/apply + bulk manual."""
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.category import Category
from app.models.categorization_rule import CategorizationRule
from app.models.transaction import Transaction, TransactionCategorizationSource
from app.parsers.base import ParsedStatement, ParsedTransaction
from app.services.imports import ingest_parsed_statement


def test_e2e_plan2_full_flow(
    client: TestClient, auth_user_with_bank_account, db_session,
) -> None:
    bank_account = auth_user_with_bank_account["bank_account"]
    ptxs = [
        ParsedTransaction(
            operation_date=date(2026, 3, i + 1),
            value_date=date(2026, 3, i + 1),
            amount=Decimal("-100"),
            label=lbl,
            raw_label=lbl,
            statement_row_index=i,
        )
        for i, lbl in enumerate([
            "PRLV URSSAF 111", "PRLV URSSAF 222", "EDF FACT", "AUTRE TRUC",
        ])
    ]
    statement = ParsedStatement(
        bank_code="DELUBAC",
        iban=bank_account.iban or "FR00",
        account_number=bank_account.iban or "FR00",
        period_start=date(2026, 3, 1),
        period_end=date(2026, 3, 31),
        opening_balance=Decimal("0"),
        closing_balance=Decimal("-400"),
        transactions=ptxs,
    )
    ir = ingest_parsed_statement(
        db_session, bank_account_id=bank_account.id, statement=statement,
    )
    db_session.commit()

    auto_count = ir.audit.get("categorized_count", 0)
    assert auto_count >= 3, f"Auto-cat attendu ≥ 3, obtenu {auto_count}"

    cat_autre = Category(name="Mon auto", slug="mon-auto-e2e", is_system=False)
    db_session.add(cat_autre)
    db_session.commit()

    r_preview = client.post("/api/rules/preview", json={
        "name": "AUTRE",
        "priority": 9500,
        "label_operator": "CONTAINS",
        "label_value": "AUTRE TRUC",
        "direction": "ANY",
        "category_id": cat_autre.id,
    })
    assert r_preview.status_code == 200, r_preview.text
    assert r_preview.json()["matching_count"] == 1

    r_create = client.post("/api/rules", json={
        "name": "AUTRE",
        "priority": 9500,
        "label_operator": "CONTAINS",
        "label_value": "AUTRE TRUC",
        "direction": "ANY",
        "category_id": cat_autre.id,
    })
    assert r_create.status_code == 201, r_create.text
    rule_id = r_create.json()["id"]

    r_apply = client.post(f"/api/rules/{rule_id}/apply")
    assert r_apply.status_code == 200, r_apply.text
    assert r_apply.json()["updated_count"] == 1

    tx_urssaf = db_session.execute(
        select(Transaction).where(
            Transaction.import_id == ir.id,
            Transaction.normalized_label.like("%URSSAF 111%"),
        )
    ).scalar_one()

    r_bulk = client.post("/api/transactions/bulk-categorize", json={
        "transaction_ids": [tx_urssaf.id],
        "category_id": cat_autre.id,
    })
    assert r_bulk.status_code == 200, r_bulk.text

    db_session.refresh(tx_urssaf)
    assert tx_urssaf.categorized_by == TransactionCategorizationSource.MANUAL
    assert tx_urssaf.category_id == cat_autre.id

    urssaf_rule = db_session.execute(
        select(CategorizationRule).where(
            CategorizationRule.is_system.is_(True),
            CategorizationRule.label_value == "URSSAF",
        )
    ).scalar_one()
    r_reapply = client.post(f"/api/rules/{urssaf_rule.id}/apply")
    assert r_reapply.status_code == 200, r_reapply.text
    db_session.refresh(tx_urssaf)
    assert tx_urssaf.categorized_by == TransactionCategorizationSource.MANUAL
    assert tx_urssaf.category_id == cat_autre.id
