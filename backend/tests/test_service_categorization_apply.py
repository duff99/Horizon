"""Tests de preview_rule et apply_rule."""
from datetime import date
from decimal import Decimal

from app.models.transaction import Transaction, TransactionCategorizationSource
from app.models.categorization_rule import (
    CategorizationRule, RuleLabelOperator, RuleDirection,
)
from app.models.category import Category
from app.models.import_record import ImportRecord, ImportStatus
from app.services.categorization import preview_rule, apply_rule


def _cat(db_session, slug: str) -> Category:
    c = Category(name=slug, slug=slug, is_system=False)
    db_session.add(c); db_session.commit()
    return c


def _mk_tx(db_session, bank_account, label: str, row_idx: int,
           amount: Decimal = Decimal("-50")) -> Transaction:
    imp = ImportRecord(
        bank_account_id=bank_account.id, filename="p.pdf",
        file_sha256="b"*64, bank_code="DELUBAC", status=ImportStatus.COMPLETED,
    )
    db_session.add(imp); db_session.commit()
    tx = Transaction(
        bank_account_id=bank_account.id, import_id=imp.id,
        operation_date=date(2026, 1, 1), value_date=date(2026, 1, 1),
        amount=amount, label=label, raw_label=label, normalized_label=label,
        dedup_key=f"{row_idx}-" + "p"*60, statement_row_index=row_idx,
    )
    db_session.add(tx); db_session.commit()
    return tx


def test_preview_counts_matching_not_manual(db_session, bank_account) -> None:
    cat = _cat(db_session, "cp-a")
    for i in range(3):
        _mk_tx(db_session, bank_account, "URSSAF PRLV", row_idx=100 + i)
    t_manual = _mk_tx(db_session, bank_account, "URSSAF DU MOIS", row_idx=200)
    t_manual.categorized_by = TransactionCategorizationSource.MANUAL
    t_manual.category_id = cat.id
    db_session.commit()

    rule = CategorizationRule(
        name="URSSAF", priority=100, direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="URSSAF",
        category_id=cat.id,
    )
    db_session.add(rule); db_session.commit()

    result = preview_rule(db_session, rule, sample_limit=10)
    assert result.matching_count == 3
    assert len(result.sample) == 3


def test_apply_updates_only_non_manual(db_session, bank_account) -> None:
    cat_x = _cat(db_session, "cx-a")
    cat_y = _cat(db_session, "cx-b")
    tx_none = _mk_tx(db_session, bank_account, "EDF FACT", row_idx=300)
    tx_rule = _mk_tx(db_session, bank_account, "EDF MONTH", row_idx=301)
    tx_rule.categorized_by = TransactionCategorizationSource.RULE
    tx_rule.category_id = cat_y.id
    tx_manual = _mk_tx(db_session, bank_account, "EDF MANUAL", row_idx=302)
    tx_manual.categorized_by = TransactionCategorizationSource.MANUAL
    tx_manual.category_id = cat_y.id
    db_session.commit()

    rule = CategorizationRule(
        name="EDF", priority=500, direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="EDF",
        category_id=cat_x.id,
    )
    db_session.add(rule); db_session.commit()

    report = apply_rule(db_session, rule)
    db_session.refresh(tx_none); db_session.refresh(tx_rule); db_session.refresh(tx_manual)

    assert report.updated_count == 2
    assert tx_none.category_id == cat_x.id
    assert tx_none.categorized_by == TransactionCategorizationSource.RULE
    assert tx_rule.category_id == cat_x.id
    assert tx_manual.category_id == cat_y.id
    assert tx_manual.categorized_by == TransactionCategorizationSource.MANUAL
