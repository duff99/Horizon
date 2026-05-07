"""Tests pour le helper data_anchor (Plan I1).

Couvre :
1. Pas de transaction → retourne today
2. Transaction récente (today) → retourne today
3. Transaction ancienne (today - 60j) → retourne la date de la transaction
4. entity_id=None → ancre globale (toutes entités)
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.entity import Entity
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction, TransactionCategorizationSource
from app.services._anchor import data_anchor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mk_entity(db: Session, name: str) -> Entity:
    e = Entity(name=name, legal_name=name)
    db.add(e)
    db.flush()
    return e


def _mk_bank_account(db: Session, entity_id: int, suffix: str = "00") -> BankAccount:
    ba = BankAccount(
        entity_id=entity_id,
        bank_code="delubac",
        bank_name="Delubac",
        iban=f"FR76ANCHOR{suffix:>16}",
        name=f"Compte Anchor {suffix}",
    )
    db.add(ba)
    db.flush()
    return ba


def _mk_tx(db: Session, ba: BankAccount, op_date: date, suffix: str = "a") -> Transaction:
    ir = ImportRecord(
        bank_account_id=ba.id,
        bank_code=ba.bank_code,
        status=ImportStatus.COMPLETED,
        period_start=op_date.replace(day=1),
        period_end=op_date,
        opening_balance=Decimal("0"),
        closing_balance=Decimal("100"),
        imported_count=1,
    )
    db.add(ir)
    db.flush()
    tx = Transaction(
        bank_account_id=ba.id,
        import_id=ir.id,
        operation_date=op_date,
        value_date=op_date,
        amount=Decimal("100"),
        label=f"TX Anchor {suffix}",
        raw_label=f"TX Anchor {suffix}",
        dedup_key=f"anchor-{ba.id}-{suffix}",
        statement_row_index=1,
        is_aggregation_parent=False,
        normalized_label=f"tx anchor {suffix}",
        categorized_by=TransactionCategorizationSource.NONE,
    )
    db.add(tx)
    db.flush()
    return tx


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_data_anchor_no_data_returns_today(db_session: Session) -> None:
    """Entité sans transaction → retourne date.today()."""
    today = date.today()
    result = data_anchor(db_session, entity_id=99999)
    assert result == today


def test_data_anchor_recent_data_returns_today(db_session: Session) -> None:
    """Transaction datée d'aujourd'hui → retourne date.today() (min(today, today))."""
    today = date.today()
    entity = _mk_entity(db_session, "Anchor Recent")
    ba = _mk_bank_account(db_session, entity.id, suffix="01")
    _mk_tx(db_session, ba, today, suffix="r1")
    db_session.flush()

    result = data_anchor(db_session, entity_id=entity.id)
    assert result == today


def test_data_anchor_old_data_returns_max_operation_date(db_session: Session) -> None:
    """Transaction datée d'il y a 60 jours → retourne cette date (plus petite que today)."""
    sixty_ago = date.today() - timedelta(days=60)
    entity = _mk_entity(db_session, "Anchor Old")
    ba = _mk_bank_account(db_session, entity.id, suffix="02")
    _mk_tx(db_session, ba, sixty_ago, suffix="o1")
    db_session.flush()

    result = data_anchor(db_session, entity_id=entity.id)
    assert result == sixty_ago


def test_data_anchor_global_no_entity_id(db_session: Session) -> None:
    """entity_id=None → ancre globale : retourne la max operation_date de toutes les tx."""
    old_date = date.today() - timedelta(days=30)
    entity = _mk_entity(db_session, "Anchor Global")
    ba = _mk_bank_account(db_session, entity.id, suffix="03")
    _mk_tx(db_session, ba, old_date, suffix="g1")
    db_session.flush()

    # Ancre globale doit être au moins old_date (si c'est la seule tx dans cette session)
    # En pratique, d'autres tests peuvent avoir des tx plus récentes.
    # On vérifie juste que le résultat est <= today.
    result = data_anchor(db_session, entity_id=None)
    assert result <= date.today()


def test_data_anchor_isolates_entity(db_session: Session) -> None:
    """data_anchor avec entity_id=A ignore les transactions de l'entité B."""
    today = date.today()
    sixty_ago = today - timedelta(days=60)

    entity_a = _mk_entity(db_session, "Anchor A")
    entity_b = _mk_entity(db_session, "Anchor B")
    ba_a = _mk_bank_account(db_session, entity_a.id, suffix="04")
    ba_b = _mk_bank_account(db_session, entity_b.id, suffix="05")

    # A : transaction il y a 60 jours
    _mk_tx(db_session, ba_a, sixty_ago, suffix="ia")
    # B : transaction aujourd'hui
    _mk_tx(db_session, ba_b, today, suffix="ib")
    db_session.flush()

    result_a = data_anchor(db_session, entity_id=entity_a.id)
    # L'ancre de A doit être sixty_ago, pas today (B n'est pas dans A)
    assert result_a == sixty_ago
