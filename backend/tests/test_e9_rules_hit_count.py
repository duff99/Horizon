"""E9 — GET /api/rules retourne un champ hit_count par règle."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.categorization_rule import CategorizationRule, RuleDirection, RuleLabelOperator
from app.models.category import Category
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction, TransactionCategorizationSource
from app.models.bank_account import BankAccount
from app.models.entity import Entity
from app.models.user import User


def _make_category(db_session: Session, name: str, slug: str) -> Category:
    cat = Category(name=name, slug=slug, is_system=False)
    db_session.add(cat)
    db_session.flush()
    return cat


def _make_rule(db_session: Session, name: str, priority: int, cat_id: int) -> CategorizationRule:
    rule = CategorizationRule(
        name=name,
        priority=priority,
        is_system=False,
        label_operator=RuleLabelOperator.CONTAINS,
        label_value=name.upper().replace(" ", ""),
        direction=RuleDirection.ANY,
        category_id=cat_id,
    )
    db_session.add(rule)
    db_session.flush()
    return rule


def _make_bank_account_and_import(db_session: Session, suffix: str) -> tuple[BankAccount, ImportRecord]:
    entity = Entity(name=f"E9 Test Entity {suffix}", legal_name=f"E9 Test {suffix}")
    db_session.add(entity)
    db_session.flush()
    ba = BankAccount(
        entity_id=entity.id,
        bank_code="delubac",
        bank_name="Delubac",
        iban=f"FR760{suffix:0>20}",
        name=f"Compte E9 {suffix}",
    )
    db_session.add(ba)
    db_session.flush()
    imp = ImportRecord(
        bank_account_id=ba.id,
        bank_code="delubac",
        status=ImportStatus.COMPLETED,
        file_sha256=f"{'e9' + suffix:0<64}"[:64],
        filename=f"e9_{suffix}.pdf",
    )
    db_session.add(imp)
    db_session.flush()
    return ba, imp


def test_rules_list_includes_hit_count(
    client: TestClient, db_session: Session, auth_user: User
) -> None:
    cat = _make_category(db_session, "Hit Count Test", f"hit-count-test-{id(auth_user)}")
    rule = _make_rule(db_session, f"HitCountTestRule{id(auth_user)}", 9980, cat.id)
    ba, imp = _make_bank_account_and_import(db_session, f"a{id(auth_user)}"[:20])

    for i in range(3):
        tx = Transaction(
            bank_account_id=ba.id,
            import_id=imp.id,
            label=f"HITCOUNT TX {i}",
            raw_label=f"HITCOUNT TX {i}",
            normalized_label=f"HITCOUNT TX {i}",
            amount=Decimal("-10.00"),
            operation_date=date(2026, 1, 1),
            value_date=date(2026, 1, 1),
            dedup_key=f"e9hc{id(auth_user)}{i:020d}"[:64],
            statement_row_index=i,
            categorization_rule_id=rule.id,
            category_id=cat.id,
            categorized_by=TransactionCategorizationSource.RULE,
        )
        db_session.add(tx)
    db_session.commit()

    resp = client.get("/api/rules?scope=all")
    assert resp.status_code == 200
    rules = resp.json()
    hit_rule = next((r for r in rules if r["name"] == rule.name), None)
    assert hit_rule is not None
    assert "hit_count" in hit_rule
    assert hit_rule["hit_count"] == 3


def test_rules_with_zero_hits(
    client: TestClient, db_session: Session, auth_user: User
) -> None:
    cat = _make_category(db_session, "Zero Hits", f"zero-hits-{id(auth_user)}")
    rule = _make_rule(db_session, f"ZeroHitRule{id(auth_user)}", 9981, cat.id)
    db_session.commit()

    resp = client.get("/api/rules?scope=all")
    assert resp.status_code == 200
    rules = resp.json()
    zero_rule = next((r for r in rules if r["name"] == rule.name), None)
    assert zero_rule is not None
    assert zero_rule["hit_count"] == 0
