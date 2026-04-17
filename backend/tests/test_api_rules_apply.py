"""POST /api/rules/{id}/apply."""
from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient

from app.models.category import Category
from app.models.categorization_rule import (
    CategorizationRule, RuleLabelOperator, RuleDirection,
)
from app.models.transaction import Transaction, TransactionCategorizationSource
from app.models.import_record import ImportRecord, ImportStatus


def test_apply_rule_updates_matching_non_manual(
    client: TestClient, auth_user, db_session, bank_account,
) -> None:
    cat = Category(name="c", slug="c-api-apply", is_system=False)
    db_session.add(cat); db_session.commit()
    rule = CategorizationRule(
        name="R", priority=8500, entity_id=None,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="ZZ",
        category_id=cat.id,
    )
    db_session.add(rule); db_session.commit()

    imp = ImportRecord(
        bank_account_id=bank_account.id, filename="a.pdf",
        file_sha256="z"*64, bank_code="DELUBAC", status=ImportStatus.COMPLETED,
    )
    db_session.add(imp); db_session.commit()
    for i in range(2):
        db_session.add(Transaction(
            bank_account_id=bank_account.id, import_id=imp.id,
            operation_date=date(2026, 1, i + 1), value_date=date(2026, 1, i + 1),
            amount=Decimal("-10"), label="ZZ", raw_label="ZZ",
            normalized_label="ZZ",
            dedup_key=f"ap-{i}-" + "z"*58, statement_row_index=i,
        ))
    db_session.commit()

    r = client.post(f"/api/rules/{rule.id}/apply")
    assert r.status_code == 200, r.text
    assert r.json()["updated_count"] == 2
