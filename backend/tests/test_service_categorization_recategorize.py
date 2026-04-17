"""Tests de recategorize_entity : reset + re-application."""
from datetime import date
from decimal import Decimal

from app.models.transaction import Transaction, TransactionCategorizationSource
from app.models.categorization_rule import (
    CategorizationRule, RuleLabelOperator, RuleDirection,
)
from app.models.category import Category
from app.models.import_record import ImportRecord, ImportStatus
from app.services.categorization import recategorize_entity


def _cat(db_session, slug: str) -> Category:
    c = Category(name=slug, slug=slug, is_system=False)
    db_session.add(c); db_session.commit()
    return c


def test_recategorize_resets_non_manual_and_re_runs(
    db_session, bank_account, entity,
) -> None:
    new_cat = _cat(db_session, "new-after-reorder")
    other_cat = _cat(db_session, "initial-cat")

    imp = ImportRecord(
        bank_account_id=bank_account.id, filename="r.pdf",
        file_sha256="c"*64, bank_code="DELUBAC", status=ImportStatus.COMPLETED,
    )
    db_session.add(imp); db_session.commit()
    tx_rule = Transaction(
        bank_account_id=bank_account.id, import_id=imp.id,
        operation_date=date(2026, 1, 1), value_date=date(2026, 1, 1),
        amount=Decimal("-100"), label="URSSAF", raw_label="URSSAF",
        normalized_label="URSSAF",
        dedup_key="r1-" + "c"*60, statement_row_index=0,
        category_id=other_cat.id,
        categorized_by=TransactionCategorizationSource.RULE,
    )
    tx_manual = Transaction(
        bank_account_id=bank_account.id, import_id=imp.id,
        operation_date=date(2026, 1, 2), value_date=date(2026, 1, 2),
        amount=Decimal("-50"), label="URSSAF B", raw_label="URSSAF B",
        normalized_label="URSSAF B",
        dedup_key="r2-" + "c"*60, statement_row_index=1,
        category_id=other_cat.id,
        categorized_by=TransactionCategorizationSource.MANUAL,
    )
    db_session.add_all([tx_rule, tx_manual]); db_session.commit()

    db_session.add(CategorizationRule(
        name="URSSAF NEW", priority=10, entity_id=None,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="URSSAF",
        category_id=new_cat.id,
    ))
    db_session.commit()

    report = recategorize_entity(db_session, entity.id)
    db_session.refresh(tx_rule); db_session.refresh(tx_manual)

    assert report.updated_count >= 1
    assert tx_rule.category_id == new_cat.id
    assert tx_rule.categorized_by == TransactionCategorizationSource.RULE
    assert tx_manual.category_id == other_cat.id
    assert tx_manual.categorized_by == TransactionCategorizationSource.MANUAL
