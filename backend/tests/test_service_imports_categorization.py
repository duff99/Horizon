"""Intégration : un import Plan 1 doit remplir normalized_label et auto-catégoriser."""
from datetime import date
from decimal import Decimal

from app.parsers.base import ParsedStatement, ParsedTransaction
from app.models.transaction import Transaction, TransactionCategorizationSource
from app.models.categorization_rule import (
    CategorizationRule, RuleLabelOperator, RuleDirection,
)
from app.models.category import Category
from app.services.imports import ingest_parsed_statement


def test_import_populates_normalized_label_and_categorizes(
    db_session, bank_account, entity,
) -> None:
    cat = Category(name="URSSAF test cat", slug="urssaf-test-cat-imp", is_system=False)
    db_session.add(cat); db_session.commit()

    rule = CategorizationRule(
        name="URSSAF-imp", priority=50, entity_id=None,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="URSSAF",
        category_id=cat.id,
    )
    db_session.add(rule); db_session.commit()

    ptx1 = ParsedTransaction(
        operation_date=date(2026, 3, 1), value_date=date(2026, 3, 1),
        amount=Decimal("-100.00"),
        label="PRLV URSSAF REF 123", raw_label="PRLV URSSAF REF 123",
        statement_row_index=0,
    )
    ptx2 = ParsedTransaction(
        operation_date=date(2026, 3, 2), value_date=date(2026, 3, 2),
        amount=Decimal("-50.00"),
        label="BOULANGERIE", raw_label="BOULANGERIE",
        statement_row_index=1,
    )
    statement = ParsedStatement(
        bank_code="DELUBAC",
        account_number=bank_account.account_number or "0000000000",
        iban=bank_account.iban or "FR0000000000",
        period_start=date(2026, 3, 1), period_end=date(2026, 3, 31),
        opening_balance=Decimal("0.00"),
        closing_balance=Decimal("-150.00"),
        transactions=[ptx1, ptx2],
    )

    ir = ingest_parsed_statement(
        db_session,
        bank_account_id=bank_account.id,
        statement=statement,
    )

    from sqlalchemy import select
    txs = db_session.execute(
        select(Transaction).where(Transaction.import_id == ir.id)
        .order_by(Transaction.statement_row_index.asc())
    ).scalars().all()
    assert len(txs) == 2
    assert all(t.normalized_label != "" for t in txs)
    assert txs[0].categorized_by == TransactionCategorizationSource.RULE
    assert txs[0].category_id == cat.id
    assert txs[1].categorized_by == TransactionCategorizationSource.NONE
    assert ir.audit.get("categorized_count") == 1
