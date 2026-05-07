"""Tests pour l'ancrage MAX(operation_date) — commit C2.

Ces tests vérifient que les widgets compute_* utilisent la dernière
transaction (MAX(operation_date)) comme ancre temporelle plutôt que
date.today(), ce qui évite de pointer sur un mois vide entre imports.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.category import Category
from app.models.entity import Entity
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction
from app.models.user import User
from app.models.user_entity_access import UserEntityAccess
from app.services.analysis import (
    _resolve_anchor_month,
    compute_category_drift,
    compute_top_movers,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _add_months(d: date, months: int) -> date:
    d = d.replace(day=1)
    total = d.year * 12 + (d.month - 1) + months
    year, m_idx = divmod(total, 12)
    return date(year, m_idx + 1, 1)


def _mk_entity_with_ba(db: Session, name: str = "AnchorCo"):
    e = Entity(name=name, legal_name=name)
    db.add(e)
    db.flush()
    ba = BankAccount(
        entity_id=e.id,
        bank_code="delubac",
        bank_name="Delubac",
        iban=f"FR76{abs(hash(name)) % 10**22:022d}",
        name="Compte test",
    )
    db.add(ba)
    db.commit()
    db.refresh(ba)
    return e, ba


def _mk_tx(
    db: Session,
    ba: BankAccount,
    *,
    amount: Decimal,
    op_date: date,
    label: str = "tx",
    category_id: int | None = None,
) -> Transaction:
    rec = ImportRecord(
        bank_account_id=ba.id,
        bank_code="delubac",
        status=ImportStatus.COMPLETED,
    )
    db.add(rec)
    db.flush()
    tx = Transaction(
        bank_account_id=ba.id,
        import_id=rec.id,
        operation_date=op_date,
        value_date=op_date,
        amount=amount,
        label=label,
        raw_label=label,
        normalized_label=label.lower(),
        dedup_key=f"k-{op_date}-{label}-{amount}-{rec.id}",
        statement_row_index=0,
        category_id=category_id,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def _get_or_create_category(db: Session, slug: str, name: str) -> Category:
    cat = db.query(Category).filter_by(slug=slug).first()
    if cat is None:
        cat = Category(slug=slug, name=name, is_system=False)
        db.add(cat)
        db.commit()
    return cat


# ---------------------------------------------------------------------------
# Tests C2 : _resolve_anchor_month
# ---------------------------------------------------------------------------


def test_anchor_uses_max_operation_date(db_session: Session):
    """Entité avec tx jusqu'au 2026-04-15 → anchor = 2026-04-01."""
    e, ba = _mk_entity_with_ba(db_session, "Anchor2026")
    _mk_tx(db_session, ba, amount=Decimal("-100"), op_date=date(2026, 4, 15), label="a1")
    _mk_tx(db_session, ba, amount=Decimal("-200"), op_date=date(2026, 3, 10), label="a2")
    _mk_tx(db_session, ba, amount=Decimal("-300"), op_date=date(2026, 1, 5), label="a3")

    anchor = _resolve_anchor_month(db_session, e.id)
    assert anchor == date(2026, 4, 1)


def test_anchor_none_when_no_data(db_session: Session):
    """Entité sans transactions → _resolve_anchor_month retourne None."""
    e, _ba = _mk_entity_with_ba(db_session, "EmptyAnchorCo")
    anchor = _resolve_anchor_month(db_session, e.id)
    assert anchor is None


# ---------------------------------------------------------------------------
# Tests C2 : compute_category_drift avec ancrage
# ---------------------------------------------------------------------------


def test_drift_returns_window_month(db_session: Session):
    """Entité avec data jusqu'à avril 2026 → window_month == '2026-04'."""
    e, ba = _mk_entity_with_ba(db_session, "DriftAnchorCo")
    cat = _get_or_create_category(db_session, "loyer-anchor", "Loyer Anchor")

    # Ancre = avril 2026. target_first = M-1 = mars 2026.
    # On met des tx sur avril (ancre), mars (target = current_key), et les 3m précédents.
    # avril : 1 tx pour ancrer
    _mk_tx(db_session, ba, amount=Decimal("-500"), op_date=date(2026, 4, 15), label="apr", category_id=cat.id)
    # mars (target, M-1) : tx qui sera le "current" de la dérive
    _mk_tx(db_session, ba, amount=Decimal("-1500"), op_date=date(2026, 3, 10), label="mar", category_id=cat.id)
    # fev, jan, dec (M-2, M-3, M-4 par rapport à l'ancre = M-1 par rapport au target)
    _mk_tx(db_session, ba, amount=Decimal("-1000"), op_date=date(2026, 2, 10), label="feb", category_id=cat.id)
    _mk_tx(db_session, ba, amount=Decimal("-1000"), op_date=date(2026, 1, 10), label="jan", category_id=cat.id)
    _mk_tx(db_session, ba, amount=Decimal("-1000"), op_date=date(2025, 12, 10), label="dec", category_id=cat.id)

    result = compute_category_drift(db_session, entity_id=e.id, seuil_pct=20.0)
    assert result.window_month == "2026-03"


def test_drift_empty_when_no_data(db_session: Session):
    """Entité sans data → window_month is None, rows == []."""
    e, _ba = _mk_entity_with_ba(db_session, "NoDataDriftCo")

    result = compute_category_drift(db_session, entity_id=e.id, seuil_pct=20.0)
    assert result.window_month is None
    assert result.rows == []


def test_top_movers_returns_window_month(db_session: Session):
    """compute_top_movers expose window_month non-None si data présente."""
    e, ba = _mk_entity_with_ba(db_session, "TopMoversAnchorCo")
    cat = _get_or_create_category(db_session, "sales-anchor", "Ventes Anchor")

    # Tx jusqu'en avril 2026
    _mk_tx(db_session, ba, amount=Decimal("1000"), op_date=date(2026, 4, 15), label="ap", category_id=cat.id)
    _mk_tx(db_session, ba, amount=Decimal("800"), op_date=date(2026, 3, 10), label="mp", category_id=cat.id)

    result = compute_top_movers(db_session, entity_id=e.id, limit=5)
    assert result.window_month is not None
    assert result.window_month == "2026-04"


def test_top_movers_window_month_none_when_no_data(db_session: Session):
    """compute_top_movers → window_month is None si entité sans data."""
    e, _ba = _mk_entity_with_ba(db_session, "EmptyTopMoversCo")

    result = compute_top_movers(db_session, entity_id=e.id, limit=5)
    assert result.window_month is None
    assert result.increases == []
    assert result.decreases == []
