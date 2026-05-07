"""TDD C4 — Les règles de catégorisation ne doivent pas matcher les enfants d'agrégat.

Contexte : une transaction agrégat (is_aggregation_parent=True, parent_transaction_id=None)
représente un VIR SEPA groupé ; ses enfants (parent_transaction_id=<id>) portent le détail
unitaire. Seul le parent doit être catégorisé par les règles automatiques.
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

def test_matches_transaction_ignores_children(db_session, bank_account) -> None:
    """matches_transaction doit retourner False pour tout enfant d'agrégat."""
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

    # Le parent doit matcher
    assert matches_transaction(rule, parent) is True, (
        "Le parent (is_aggregation_parent=True, parent_transaction_id=None) "
        "doit matcher la règle."
    )

    # Aucun enfant ne doit matcher
    for child in children:
        assert matches_transaction(rule, child) is False, (
            f"L'enfant #{child.id} (parent_transaction_id={child.parent_transaction_id}) "
            "ne doit PAS matcher la règle."
        )


def test_apply_rule_skips_children(db_session, bank_account) -> None:
    """apply_rule doit mettre à jour 1 ligne uniquement (le parent), pas 4."""
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

    # Exactement 1 ligne mise à jour (le parent uniquement)
    assert report.updated_count == 1, (
        f"apply_rule a mis à jour {report.updated_count} ligne(s) au lieu de 1. "
        "Les enfants d'agrégat ne doivent pas être catégorisés."
    )

    db_session.refresh(parent)
    for child in children:
        db_session.refresh(child)

    assert parent.category_id == cat.id, "Le parent doit avoir été catégorisé."
    assert parent.categorized_by == TransactionCategorizationSource.RULE

    for child in children:
        assert child.category_id is None, (
            f"L'enfant #{child.id} ne doit pas être catégorisé."
        )
        assert child.categorized_by == TransactionCategorizationSource.NONE
