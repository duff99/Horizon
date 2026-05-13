"""Règles de catégorisation : périmètre vis-à-vis des agrégats SEPA.

Convention : la transaction synthétique `is_aggregation_parent=True`
résume la somme de ses enfants et n'a pas de sémantique métier propre —
elle ne doit JAMAIS être catégorisée par une règle. À l'inverse, les
enfants (lignes unitaires, commissions, etc.) sont des transactions
réelles qui doivent pouvoir être catégorisées sinon elles restent
indéfiniment dans la rubrique "non catégorisées" du prévisionnel.
"""
from datetime import date
from decimal import Decimal

import pytest

from app.models.categorization_rule import (
    CategorizationRule, RuleDirection, RuleLabelOperator,
)
from app.models.category import Category
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction, TransactionCategorizationSource
from app.services.categorization import apply_rule, matches_transaction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_import(db_session, bank_account_id: int, suffix: str) -> ImportRecord:
    imp = ImportRecord(
        bank_account_id=bank_account_id,
        filename=f"import_{suffix}.pdf",
        file_sha256=f"a{suffix}"[:64].ljust(64, "0"),
        bank_code="DELUBAC",
        status=ImportStatus.COMPLETED,
    )
    db_session.add(imp)
    db_session.commit()
    return imp


def _make_tx(
    db_session,
    bank_account_id: int,
    import_id: int,
    *,
    normalized_label: str,
    amount: Decimal,
    row_idx: int,
    is_aggregation_parent: bool = False,
    parent_transaction_id: int | None = None,
) -> Transaction:
    tx = Transaction(
        bank_account_id=bank_account_id,
        import_id=import_id,
        operation_date=date(2026, 1, 15),
        value_date=date(2026, 1, 15),
        amount=amount,
        label=normalized_label,
        raw_label=normalized_label,
        normalized_label=normalized_label,
        dedup_key=f"tva-{row_idx}-" + "x" * 50,
        statement_row_index=row_idx,
        is_aggregation_parent=is_aggregation_parent,
        parent_transaction_id=parent_transaction_id,
        categorized_by=TransactionCategorizationSource.NONE,
    )
    db_session.add(tx)
    db_session.commit()
    return tx


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_matches_transaction_ignores_aggregation_parent_but_keeps_children(
    db_session, bank_account
) -> None:
    """matches_transaction : parent synthétique ignoré, enfants matchables."""
    imp = _make_import(db_session, bank_account.id, "tva1")

    parent = _make_tx(
        db_session, bank_account.id, imp.id,
        normalized_label="TVA VIR SEPA",
        amount=Decimal("-300.00"),
        row_idx=1000,
        is_aggregation_parent=True,
        parent_transaction_id=None,
    )

    children = [
        _make_tx(
            db_session, bank_account.id, imp.id,
            normalized_label=f"TVA VIR SEPA #{i}",
            amount=Decimal("-100.00"),
            row_idx=1001 + i,
            is_aggregation_parent=False,
            parent_transaction_id=parent.id,
        )
        for i in range(3)
    ]

    cat = Category(name="TVA-test", slug="tva-test", is_system=False)
    db_session.add(cat)
    db_session.commit()

    rule = CategorizationRule(
        name="Regle TVA test",
        priority=10,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS,
        label_value="TVA",
        category_id=cat.id,
    )
    db_session.add(rule)
    db_session.commit()

    # Le parent synthétique ne doit JAMAIS matcher (pas de sémantique propre).
    assert matches_transaction(rule, parent) is False, (
        "Le parent synthétique (is_aggregation_parent=True) ne doit pas matcher."
    )

    # Les enfants doivent matcher : ce sont des tx réelles, comptées par le
    # forecast et listées dans la page Transactions.
    for child in children:
        assert matches_transaction(rule, child) is True, (
            f"L'enfant #{child.id} doit pouvoir être catégorisé par la règle."
        )


def test_apply_rule_catches_children_skips_aggregation_parent(
    db_session, bank_account
) -> None:
    """apply_rule met à jour les enfants (3) mais saute le parent synthétique."""
    imp = _make_import(db_session, bank_account.id, "tva2")

    parent = _make_tx(
        db_session, bank_account.id, imp.id,
        normalized_label="TVA VIR SEPA",
        amount=Decimal("-300.00"),
        row_idx=2000,
        is_aggregation_parent=True,
        parent_transaction_id=None,
    )

    children = [
        _make_tx(
            db_session, bank_account.id, imp.id,
            normalized_label=f"TVA VIR SEPA #{i}",
            amount=Decimal("-100.00"),
            row_idx=2001 + i,
            is_aggregation_parent=False,
            parent_transaction_id=parent.id,
        )
        for i in range(3)
    ]

    cat = Category(name="TVA-apply-test", slug="tva-apply-test", is_system=False)
    db_session.add(cat)
    db_session.commit()

    rule = CategorizationRule(
        name="Regle TVA apply test",
        priority=20,
        direction=RuleDirection.ANY,
        label_operator=RuleLabelOperator.CONTAINS,
        label_value="TVA",
        category_id=cat.id,
    )
    db_session.add(rule)
    db_session.commit()

    report = apply_rule(db_session, rule)

    # Exactement 3 enfants catégorisés ; le parent synthétique est sauté.
    assert report.updated_count == 3, (
        f"apply_rule a mis à jour {report.updated_count} ligne(s) au lieu de 3. "
        "Les enfants SEPA doivent être catégorisables ; seul le parent "
        "synthétique est exclu."
    )

    db_session.refresh(parent)
    for child in children:
        db_session.refresh(child)

    assert parent.category_id is None, (
        "Le parent synthétique ne doit pas être catégorisé."
    )
    assert parent.categorized_by == TransactionCategorizationSource.NONE

    for child in children:
        assert child.category_id == cat.id, (
            f"L'enfant #{child.id} doit avoir été catégorisé."
        )
        assert child.categorized_by == TransactionCategorizationSource.RULE
