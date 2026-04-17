"""Tests des nouvelles colonnes de catégorisation sur Transaction (Plan 2)."""
from datetime import date
from decimal import Decimal

from app.models.transaction import (
    Transaction,
    TransactionCategorizationSource,
)
from app.models.categorization_rule import (
    CategorizationRule, RuleLabelOperator, RuleDirection,
)
from app.models.category import Category
from app.models.bank_account import BankAccount
from app.models.import_record import ImportRecord, ImportStatus
from app.models.entity import Entity


def test_transaction_defaults_categorized_none(
    db_session, bank_account: BankAccount
) -> None:
    import_rec = ImportRecord(
        bank_account_id=bank_account.id, filename="x.pdf",
        file_sha256="a"*64, bank_code="DELUBAC", status=ImportStatus.COMPLETED,
    )
    db_session.add(import_rec)
    db_session.commit()

    tx = Transaction(
        bank_account_id=bank_account.id, import_id=import_rec.id,
        operation_date=date(2026, 1, 1), value_date=date(2026, 1, 1),
        amount=Decimal("10.00"), label="TEST", raw_label="TEST",
        normalized_label="TEST",
        dedup_key="x"*64, statement_row_index=0,
    )
    db_session.add(tx)
    db_session.commit()
    db_session.refresh(tx)

    assert tx.categorized_by == TransactionCategorizationSource.NONE
    assert tx.categorization_rule_id is None
    assert tx.normalized_label == "TEST"


def test_transaction_can_link_to_rule(
    db_session, bank_account: BankAccount
) -> None:
    cat = Category(name="X", slug="x-tx-cat-test", is_system=False)
    db_session.add(cat)
    db_session.commit()
    rule = CategorizationRule(
        name="R", priority=5000, direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="FOO",
        category_id=cat.id,
    )
    db_session.add(rule)

    import_rec = ImportRecord(
        bank_account_id=bank_account.id, filename="y.pdf",
        file_sha256="b"*64, bank_code="DELUBAC", status=ImportStatus.COMPLETED,
    )
    db_session.add(import_rec)
    db_session.commit()

    tx = Transaction(
        bank_account_id=bank_account.id, import_id=import_rec.id,
        operation_date=date(2026, 1, 1), value_date=date(2026, 1, 1),
        amount=Decimal("5.00"), label="FOO", raw_label="FOO",
        normalized_label="FOO",
        dedup_key="y"*64, statement_row_index=0,
        category_id=cat.id,
        categorized_by=TransactionCategorizationSource.RULE,
        categorization_rule_id=rule.id,
    )
    db_session.add(tx)
    db_session.commit()
    db_session.refresh(tx)

    assert tx.categorized_by == TransactionCategorizationSource.RULE
    assert tx.categorization_rule_id == rule.id
