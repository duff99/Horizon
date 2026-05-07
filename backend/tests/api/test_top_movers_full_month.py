"""Tests pour _last_full_month — commit C3.

Vérifie que compute_top_movers ignore les mois partiellement importés
en reculant vers le dernier mois "plein" (>= 50 % de la médiane des
6 derniers mois en nb transactions).

Cas typique : avril a 5 tx, médiane Q1 ~200 → utiliser mars comme 'current'.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.category import Category
from app.models.entity import Entity
from app.models.import_record import ImportRecord, ImportStatus
from app.models.transaction import Transaction
from app.services.analysis import _last_full_month, compute_top_movers


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _add_months(d: date, months: int) -> date:
    d = d.replace(day=1)
    total = d.year * 12 + (d.month - 1) + months
    year, m_idx = divmod(total, 12)
    return date(year, m_idx + 1, 1)


def _mk_entity_with_ba(db: Session, name: str):
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


def _mk_tx(db: Session, ba: BankAccount, *, amount: Decimal, op_date: date, label: str = "x", category_id: int | None = None) -> Transaction:
    rec = ImportRecord(bank_account_id=ba.id, bank_code="delubac", status=ImportStatus.COMPLETED)
    db.add(rec)
    db.flush()
    tx = Transaction(
        bank_account_id=ba.id, import_id=rec.id,
        operation_date=op_date, value_date=op_date,
        amount=amount, label=label, raw_label=label,
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
# Tests _last_full_month
# ---------------------------------------------------------------------------


def test_last_full_month_uses_anchor_when_full(db_session: Session):
    """Si le mois le plus récent a assez de tx, il est retenu comme 'current'."""
    e, ba = _mk_entity_with_ba(db_session, "FullMonthCo")

    # 3 mois avec 20 tx chacun → médiane = 20, threshold = 10
    # Le mois le plus récent a aussi 20 tx → suffisant
    anchor = date(2026, 3, 1)
    for m_offset in range(3):
        m = _add_months(anchor, -m_offset)
        for j in range(20):
            _mk_tx(db_session, ba, amount=Decimal("-10"), op_date=m, label=f"tx-{m_offset}-{j}")

    result = _last_full_month(db_session, e.id)
    assert result == date(2026, 3, 1)


def test_last_full_month_recedes_when_partial(db_session: Session):
    """Si le mois le plus récent est partiel (< 50 % médiane), recule d'un mois."""
    e, ba = _mk_entity_with_ba(db_session, "PartialMonthCo")

    # Q1 2026 : jan, fev, mar avec 20 tx chacun (mois pleins)
    # Avril 2026 : seulement 3 tx (< 50 % de la médiane 20) → partiel
    for m_str, n_tx in [
        (date(2026, 1, 1), 20),
        (date(2026, 2, 1), 20),
        (date(2026, 3, 1), 20),
        (date(2026, 4, 1), 3),   # partiel
    ]:
        for j in range(n_tx):
            _mk_tx(db_session, ba, amount=Decimal("-10"), op_date=m_str, label=f"tx-{m_str.month}-{j}")

    result = _last_full_month(db_session, e.id)
    # Avril partiel → recule à mars
    assert result == date(2026, 3, 1)


def test_last_full_month_none_when_no_data(db_session: Session):
    """Entité sans transactions → None."""
    e, _ba = _mk_entity_with_ba(db_session, "EmptyLastFullCo")
    assert _last_full_month(db_session, e.id) is None


# ---------------------------------------------------------------------------
# Tests compute_top_movers avec _last_full_month
# ---------------------------------------------------------------------------


def test_top_movers_window_month_skips_partial_month(db_session: Session):
    """compute_top_movers utilise le dernier mois plein, pas l'anchor partiel.

    Seed : Q1 plein (20 tx/mois), avril partiel (3 tx).
    → window_month doit être '2026-03' (mars), pas '2026-04'.
    """
    e, ba = _mk_entity_with_ba(db_session, "TopMoversFullCo")
    cat = _get_or_create_category(db_session, "sales-full", "Ventes Full")

    for m_str, n_tx in [
        (date(2026, 1, 1), 20),
        (date(2026, 2, 1), 20),
        (date(2026, 3, 1), 20),
        (date(2026, 4, 1), 3),   # partiel
    ]:
        for j in range(n_tx):
            _mk_tx(
                db_session, ba,
                amount=Decimal("-50"),
                op_date=m_str,
                label=f"tx-{m_str.month}-{j}",
                category_id=cat.id,
            )

    result = compute_top_movers(db_session, entity_id=e.id, limit=5)
    assert result.window_month == "2026-03"


def test_top_movers_window_month_uses_anchor_when_full(db_session: Session):
    """Si le mois le plus récent est plein, window_month = ce mois."""
    e, ba = _mk_entity_with_ba(db_session, "TopMoversAnchorFullCo")
    cat = _get_or_create_category(db_session, "sales-full2", "Ventes Full2")

    # 3 mois avec 20 tx chacun, dernier mois = mars 2026 (plein)
    anchor = date(2026, 3, 1)
    for m_offset in range(3):
        m = _add_months(anchor, -m_offset)
        for j in range(20):
            _mk_tx(
                db_session, ba,
                amount=Decimal("-50"),
                op_date=m,
                label=f"tx-{m_offset}-{j}",
                category_id=cat.id,
            )

    result = compute_top_movers(db_session, entity_id=e.id, limit=5)
    assert result.window_month == "2026-03"
