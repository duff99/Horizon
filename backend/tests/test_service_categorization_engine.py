"""Tests du moteur : tie-break, first-match-wins, exclusion MANUAL."""
from datetime import date
from decimal import Decimal

from app.models.transaction import Transaction, TransactionCategorizationSource
from app.models.categorization_rule import (
    CategorizationRule, RuleLabelOperator, RuleDirection,
)
from app.models.category import Category
from app.models.import_record import ImportRecord, ImportStatus
from app.services.categorization import (
    fetch_rules_for_entity, categorize_transaction,
)


def _cat(db_session, slug: str) -> Category:
    c = Category(name=slug, slug=slug, is_system=False)
    db_session.add(c); db_session.commit()
    return c


def _tx(db_session, bank_account, label: str, row_idx: int) -> Transaction:
    imp = ImportRecord(
        bank_account_id=bank_account.id, filename="t.pdf",
        file_sha256="a"*64, bank_code="DELUBAC", status=ImportStatus.COMPLETED,
    )
    db_session.add(imp); db_session.commit()
    tx = Transaction(
        bank_account_id=bank_account.id, import_id=imp.id,
        operation_date=date(2026, 1, 1), value_date=date(2026, 1, 1),
        amount=Decimal("-10.00"), label=label, raw_label=label,
        normalized_label=label,
        dedup_key=f"{row_idx}-" + "z"*60, statement_row_index=row_idx,
    )
    db_session.add(tx); db_session.commit()
    return tx


def test_entity_rule_wins_over_global_at_same_priority(
    db_session, bank_account, entity,
) -> None:
    cat_a = _cat(db_session, "cat-a")
    cat_b = _cat(db_session, "cat-b")
    db_session.add(CategorizationRule(
        name="Global", priority=500, entity_id=None,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="X",
        category_id=cat_a.id,
    ))
    db_session.add(CategorizationRule(
        name="Entity", priority=500, entity_id=entity.id,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="X",
        category_id=cat_b.id,
    ))
    db_session.commit()

    rules = fetch_rules_for_entity(db_session, entity.id)
    assert rules[0].name == "Entity"


def test_first_match_wins_by_priority(db_session, bank_account, entity) -> None:
    cat_a = _cat(db_session, "cat-fa")
    cat_b = _cat(db_session, "cat-fb")
    db_session.add(CategorizationRule(
        name="High", priority=100, entity_id=None,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="URSSAF",
        category_id=cat_a.id,
    ))
    db_session.add(CategorizationRule(
        name="Low", priority=9000, entity_id=None,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="URSSAF",
        category_id=cat_b.id,
    ))
    db_session.commit()

    tx = _tx(db_session, bank_account, "URSSAF REF 123", row_idx=10)
    result = categorize_transaction(db_session, tx, entity_id=entity.id)
    assert result is not None
    assert result.name == "High"
    assert tx.category_id == cat_a.id
    assert tx.categorized_by == TransactionCategorizationSource.RULE
    assert tx.categorization_rule_id is not None


def test_manual_never_overwritten(db_session, bank_account, entity) -> None:
    cat_a = _cat(db_session, "cat-ma")
    cat_manual = _cat(db_session, "cat-manual")
    db_session.add(CategorizationRule(
        name="M", priority=200, entity_id=None,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="X",
        category_id=cat_a.id,
    ))
    db_session.commit()

    tx = _tx(db_session, bank_account, "X", row_idx=11)
    tx.category_id = cat_manual.id
    tx.categorized_by = TransactionCategorizationSource.MANUAL
    db_session.commit()

    categorize_transaction(db_session, tx, entity_id=entity.id)
    assert tx.category_id == cat_manual.id
    assert tx.categorized_by == TransactionCategorizationSource.MANUAL


def test_no_rule_matches(db_session, bank_account, entity) -> None:
    tx = _tx(db_session, bank_account, "COMPLETELY UNKNOWN", row_idx=12)
    result = categorize_transaction(db_session, tx, entity_id=entity.id)
    assert result is None
    assert tx.category_id is None
    assert tx.categorized_by == TransactionCategorizationSource.NONE
