"""Tests de build_rule_filter et matches_transaction (moteur pur)."""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.transaction import Transaction
from app.models.categorization_rule import (
    CategorizationRule, RuleLabelOperator, RuleDirection, RuleAmountOperator,
)
from app.services.categorization import build_rule_filter, matches_transaction
from app.models.bank_account import BankAccount
from app.models.import_record import ImportRecord, ImportStatus
from app.models.category import Category


def _mk_cat(db_session, slug: str) -> Category:
    c = Category(name=slug, slug=slug, is_system=False)
    db_session.add(c); db_session.commit()
    return c


def _mk_tx(
    db_session, bank_account: BankAccount,
    *, label: str, amount: Decimal, normalized: str | None = None,
    row_idx: int = 0,
) -> Transaction:
    imp = ImportRecord(
        bank_account_id=bank_account.id, filename="t.pdf",
        file_sha256="f" * 64, bank_code="DELUBAC", status=ImportStatus.COMPLETED,
    )
    db_session.add(imp); db_session.commit()
    tx = Transaction(
        bank_account_id=bank_account.id, import_id=imp.id,
        operation_date=date(2026, 1, 1), value_date=date(2026, 1, 1),
        amount=amount, label=label, raw_label=label,
        normalized_label=normalized if normalized is not None else label.upper(),
        dedup_key=f"{row_idx}-" + "x" * 60, statement_row_index=row_idx,
    )
    db_session.add(tx); db_session.commit()
    return tx


def test_contains_matches(db_session, bank_account) -> None:
    cat = _mk_cat(db_session, "c1")
    rule = CategorizationRule(
        name="R", priority=100, direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS, label_value="URSSAF",
        category_id=cat.id,
    )
    db_session.add(rule); db_session.commit()

    tx_match = _mk_tx(db_session, bank_account,
                     label="PRLV URSSAF 123", amount=Decimal("-100"),
                     normalized="PRLV URSSAF 123", row_idx=1)
    tx_no    = _mk_tx(db_session, bank_account,
                     label="EDF", amount=Decimal("-50"), normalized="EDF", row_idx=2)

    assert matches_transaction(rule, tx_match)
    assert not matches_transaction(rule, tx_no)

    q = select(Transaction).where(build_rule_filter(rule))
    ids = {r.id for r in db_session.execute(q).scalars().all()}
    assert tx_match.id in ids and tx_no.id not in ids


def test_direction_credit(db_session, bank_account) -> None:
    cat = _mk_cat(db_session, "c2")
    rule = CategorizationRule(
        name="R2", priority=101, direction=RuleDirection.CREDIT,
        label_operator=RuleLabelOperator.CONTAINS, label_value="REMB",
        category_id=cat.id,
    )
    db_session.add(rule); db_session.commit()
    tx_pos = _mk_tx(db_session, bank_account, label="REMB X",
                    amount=Decimal("50"), row_idx=3)
    tx_neg = _mk_tx(db_session, bank_account, label="REMB Y",
                    amount=Decimal("-50"), row_idx=4)
    assert matches_transaction(rule, tx_pos)
    assert not matches_transaction(rule, tx_neg)


def test_amount_between(db_session, bank_account) -> None:
    cat = _mk_cat(db_session, "c3")
    rule = CategorizationRule(
        name="R3", priority=102, direction=RuleDirection.DEBIT,
        amount_operator=RuleAmountOperator.BETWEEN,
        amount_value=Decimal("100"), amount_value2=Decimal("200"),
        category_id=cat.id,
    )
    db_session.add(rule); db_session.commit()

    tx_ok     = _mk_tx(db_session, bank_account, label="X",
                        amount=Decimal("-150"), row_idx=5)
    tx_too_lo = _mk_tx(db_session, bank_account, label="X",
                        amount=Decimal("-50"), row_idx=6)
    tx_too_hi = _mk_tx(db_session, bank_account, label="X",
                        amount=Decimal("-300"), row_idx=7)
    assert matches_transaction(rule, tx_ok)
    assert not matches_transaction(rule, tx_too_lo)
    assert not matches_transaction(rule, tx_too_hi)


def test_starts_with(db_session, bank_account) -> None:
    cat = _mk_cat(db_session, "c4")
    rule = CategorizationRule(
        name="R4", priority=103, direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.STARTS_WITH,
        label_value="VIR SEPA", category_id=cat.id,
    )
    db_session.add(rule); db_session.commit()
    tx_a = _mk_tx(db_session, bank_account, label="VIR SEPA SALAIRE X",
                   amount=Decimal("-1000"),
                   normalized="VIR SEPA SALAIRE X", row_idx=8)
    tx_b = _mk_tx(db_session, bank_account, label="PRLV SEPA URSSAF",
                   amount=Decimal("-500"),
                   normalized="PRLV SEPA URSSAF", row_idx=9)
    assert matches_transaction(rule, tx_a)
    assert not matches_transaction(rule, tx_b)
