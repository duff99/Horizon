"""Moteur de catégorisation : matching Python + SQL, apply, preview."""
from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session
from sqlalchemy.sql import ColumnElement

from app.models.categorization_rule import (
    CategorizationRule, RuleLabelOperator, RuleAmountOperator, RuleDirection,
)
from app.models.transaction import Transaction, TransactionCategorizationSource


def build_rule_filter(rule: CategorizationRule) -> ColumnElement[bool]:
    """Retourne une clause WHERE SQLAlchemy qui matche les transactions de la règle.
    Ne filtre PAS sur categorized_by — le caller ajoute ce critère.
    """
    clauses: list[ColumnElement[bool]] = []

    if rule.label_operator is not None and rule.label_value is not None:
        pattern = rule.label_value
        if rule.label_operator == RuleLabelOperator.CONTAINS:
            clauses.append(Transaction.normalized_label.ilike(f"%{pattern}%"))
        elif rule.label_operator == RuleLabelOperator.STARTS_WITH:
            clauses.append(Transaction.normalized_label.ilike(f"{pattern}%"))
        elif rule.label_operator == RuleLabelOperator.ENDS_WITH:
            clauses.append(Transaction.normalized_label.ilike(f"%{pattern}"))
        elif rule.label_operator == RuleLabelOperator.EQUALS:
            clauses.append(Transaction.normalized_label == pattern)

    if rule.direction == RuleDirection.CREDIT:
        clauses.append(Transaction.amount > 0)
    elif rule.direction == RuleDirection.DEBIT:
        clauses.append(Transaction.amount < 0)

    if rule.amount_operator is not None and rule.amount_value is not None:
        abs_amt = func.abs(Transaction.amount)
        if rule.amount_operator == RuleAmountOperator.EQ:
            clauses.append(abs_amt == rule.amount_value)
        elif rule.amount_operator == RuleAmountOperator.NE:
            clauses.append(abs_amt != rule.amount_value)
        elif rule.amount_operator == RuleAmountOperator.GT:
            clauses.append(abs_amt > rule.amount_value)
        elif rule.amount_operator == RuleAmountOperator.LT:
            clauses.append(abs_amt < rule.amount_value)
        elif rule.amount_operator == RuleAmountOperator.BETWEEN:
            assert rule.amount_value2 is not None
            clauses.append(abs_amt >= rule.amount_value)
            clauses.append(abs_amt <= rule.amount_value2)

    if rule.counterparty_id is not None:
        clauses.append(Transaction.counterparty_id == rule.counterparty_id)

    if rule.bank_account_id is not None:
        clauses.append(Transaction.bank_account_id == rule.bank_account_id)

    return and_(*clauses) if clauses else (Transaction.id == Transaction.id)


def matches_transaction(rule: CategorizationRule, tx: Transaction) -> bool:
    """Évalue une règle contre une Transaction chargée (en Python, sans SQL)."""
    if rule.label_operator is not None and rule.label_value:
        nl = tx.normalized_label or ""
        pat = rule.label_value
        if rule.label_operator == RuleLabelOperator.CONTAINS and pat not in nl:
            return False
        if rule.label_operator == RuleLabelOperator.STARTS_WITH and not nl.startswith(pat):
            return False
        if rule.label_operator == RuleLabelOperator.ENDS_WITH and not nl.endswith(pat):
            return False
        if rule.label_operator == RuleLabelOperator.EQUALS and nl != pat:
            return False

    if rule.direction == RuleDirection.CREDIT and tx.amount <= 0:
        return False
    if rule.direction == RuleDirection.DEBIT and tx.amount >= 0:
        return False

    if rule.amount_operator is not None and rule.amount_value is not None:
        abs_amt = abs(tx.amount)
        if rule.amount_operator == RuleAmountOperator.EQ and abs_amt != rule.amount_value:
            return False
        if rule.amount_operator == RuleAmountOperator.NE and abs_amt == rule.amount_value:
            return False
        if rule.amount_operator == RuleAmountOperator.GT and not (abs_amt > rule.amount_value):
            return False
        if rule.amount_operator == RuleAmountOperator.LT and not (abs_amt < rule.amount_value):
            return False
        if rule.amount_operator == RuleAmountOperator.BETWEEN:
            v2 = rule.amount_value2 or Decimal("0")
            if not (rule.amount_value <= abs_amt <= v2):
                return False

    if rule.counterparty_id is not None and tx.counterparty_id != rule.counterparty_id:
        return False

    if rule.bank_account_id is not None and tx.bank_account_id != rule.bank_account_id:
        return False

    return True
