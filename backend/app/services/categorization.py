"""Moteur de catégorisation : matching Python + SQL, apply, preview."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from sqlalchemy import and_, func, or_, select, update
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


def fetch_rules_for_entity(
    session: Session, entity_id: int | None,
) -> list[CategorizationRule]:
    """Retourne les règles applicables à cette entité, déjà triées par
    priorité d'évaluation : règles entité d'abord (prio ASC), puis globales (prio ASC).
    Si entity_id=None, retourne uniquement les globales.
    """
    if entity_id is not None:
        entity_rules = session.execute(
            select(CategorizationRule)
            .where(CategorizationRule.entity_id == entity_id)
            .order_by(CategorizationRule.priority.asc())
        ).scalars().all()
    else:
        entity_rules = []

    global_rules = session.execute(
        select(CategorizationRule)
        .where(CategorizationRule.entity_id.is_(None))
        .order_by(CategorizationRule.priority.asc())
    ).scalars().all()

    return list(entity_rules) + list(global_rules)


def categorize_transaction(
    session: Session,
    tx: Transaction,
    *,
    entity_id: int | None,
) -> CategorizationRule | None:
    """Applique le premier match ; mute tx en place. Ne commit pas.
    Retourne la règle matchée ou None. Ne touche pas les tx MANUAL.
    """
    if tx.categorized_by == TransactionCategorizationSource.MANUAL:
        return None

    rules = fetch_rules_for_entity(session, entity_id)
    for rule in rules:
        if matches_transaction(rule, tx):
            tx.category_id = rule.category_id
            tx.categorized_by = TransactionCategorizationSource.RULE
            tx.categorization_rule_id = rule.id
            return rule
    return None


@dataclass
class RuleSample:
    id: int
    operation_date: str
    amount: Decimal
    label: str
    current_category_id: int | None


@dataclass
class RulePreviewResult:
    matching_count: int
    sample: list[RuleSample]


@dataclass
class ApplyReport:
    updated_count: int


def preview_rule(
    session: Session,
    rule: CategorizationRule,
    *,
    sample_limit: int = 20,
) -> RulePreviewResult:
    """Compte + échantillonne les transactions que la règle matcherait,
    en excluant les MANUAL. Ne mute rien.
    """
    base_filter = and_(
        build_rule_filter(rule),
        Transaction.categorized_by != TransactionCategorizationSource.MANUAL,
    )
    count = session.execute(
        select(func.count(Transaction.id)).where(base_filter)
    ).scalar_one()

    samples_rows = session.execute(
        select(Transaction).where(base_filter)
        .order_by(Transaction.operation_date.desc(), Transaction.id.desc())
        .limit(sample_limit)
    ).scalars().all()

    samples = [
        RuleSample(
            id=t.id,
            operation_date=t.operation_date.isoformat(),
            amount=t.amount,
            label=t.label,
            current_category_id=t.category_id,
        )
        for t in samples_rows
    ]
    return RulePreviewResult(matching_count=count, sample=samples)


def apply_rule(session: Session, rule: CategorizationRule) -> ApplyReport:
    """Applique la règle aux transactions non-MANUAL de son scope.
    Pour une règle entité : restreint aux tx des comptes bancaires de cette entité.
    Pour une règle globale : applique sur toutes les tx de la DB (le filtre d'accès
    par entité est fait côté API, pas ici).
    """
    from app.models.bank_account import BankAccount

    base_filter = and_(
        build_rule_filter(rule),
        Transaction.categorized_by != TransactionCategorizationSource.MANUAL,
    )
    if rule.entity_id is not None:
        accessible_accounts = select(BankAccount.id).where(
            BankAccount.entity_id == rule.entity_id
        )
        base_filter = and_(
            base_filter,
            Transaction.bank_account_id.in_(accessible_accounts),
        )

    stmt = (
        update(Transaction)
        .where(base_filter)
        .values(
            category_id=rule.category_id,
            categorized_by=TransactionCategorizationSource.RULE,
            categorization_rule_id=rule.id,
        )
    )
    result = session.execute(stmt)
    session.flush()
    return ApplyReport(updated_count=result.rowcount or 0)
