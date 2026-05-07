"""Tests pour le guard sur le calcul du drift % — commit C1.

Vérifie que les catégories peu actives (avg3m < 50 € ou < 2 mois sur 3)
reçoivent status='insufficient' et delta_pct=None plutôt qu'un
pourcentage aberrant.

Cas réel prod : entity 2, "Frais pro. remboursés",
  current=-29621 cents, avg3m=-2158 cents (jan=0, fev=0, mars=-6474)
  → sans guard : delta_pct = -1272.6 %
  → avec guard : delta_pct = None, status = 'insufficient'
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
from app.services.analysis import compute_category_drift


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
# Tests C1 : guard sur calcul drift %
# ---------------------------------------------------------------------------


def test_drift_guard_insufficient_when_one_active_month(db_session: Session):
    """Cas pathologique prod : avg3m sous le seuil + activité éparse.

    Seed : current=-29000 cents, prev_months=[0, 0, -6500 cents].
    avg3m = -6500 // 3 = -2166 cents → |avg3m| < 5000 → insufficient.
    active_prev = 1 < 2 → insufficient aussi.
    Résultat attendu : delta_pct=None, status='insufficient'.
    """
    e, ba = _mk_entity_with_ba(db_session, "GuardPathoCo")
    cat = _get_or_create_category(db_session, "frais-pro-guard", "Frais pro guard")

    # Anchor = mois courant. Target = M-1. Prev = M-2, M-3, M-4.
    today_first = date.today().replace(day=1)

    # Tx anchor (pour fixer MAX)
    _mk_tx(db_session, ba, amount=Decimal("-1"), op_date=date.today(), label="anchor", category_id=cat.id)
    # current (M-1 = target) : -290 € = -29000 cents
    _mk_tx(db_session, ba, amount=Decimal("-290"), op_date=_add_months(today_first, -1), label="cur", category_id=cat.id)
    # prev : seul M-4 actif : -65 € = -6500 cents (M-2 et M-3 = 0)
    _mk_tx(db_session, ba, amount=Decimal("-65"), op_date=_add_months(today_first, -4), label="prev-m4", category_id=cat.id)

    result = compute_category_drift(db_session, entity_id=e.id, seuil_pct=30.0)

    rows = {r.label: r for r in result.rows}
    assert "Frais pro guard" in rows, f"Catégorie absente. Rows: {rows}"
    row = rows["Frais pro guard"]
    assert row.delta_pct is None, f"delta_pct devrait être None, got {row.delta_pct}"
    assert row.status == "insufficient"


def test_drift_guard_normal_when_enough_active_months(db_session: Session):
    """Cas normal : 3 mois actifs, avg3m > 50 €, delta calculé normalement.

    Seed : current=-290 € (-29000 cents), prev=[-90, -100, -80] (centimes).
    avg3m = (-9000 + -10000 + -8000) // 3 = -9000 cents.
    delta_pct = (-29000 - -9000) / 9000 * 100 = -222.2 % → alert à seuil 30.
    """
    e, ba = _mk_entity_with_ba(db_session, "GuardNormalCo")
    cat = _get_or_create_category(db_session, "salaires-guard", "Salaires guard")

    today_first = date.today().replace(day=1)

    # Tx anchor
    _mk_tx(db_session, ba, amount=Decimal("-1"), op_date=date.today(), label="anchor", category_id=cat.id)
    # current (M-1 = target) : -290 €
    _mk_tx(db_session, ba, amount=Decimal("-290"), op_date=_add_months(today_first, -1), label="cur", category_id=cat.id)
    # prev M-2, M-3, M-4 actifs
    for i, amt in zip(range(2, 5), ["-90", "-100", "-80"]):
        _mk_tx(db_session, ba, amount=Decimal(amt), op_date=_add_months(today_first, -i), label=f"prev-{i}", category_id=cat.id)

    result = compute_category_drift(db_session, entity_id=e.id, seuil_pct=30.0)

    rows = {r.label: r for r in result.rows}
    assert "Salaires guard" in rows
    row = rows["Salaires guard"]
    assert row.delta_pct is not None, "delta_pct ne devrait pas être None"
    assert row.status in ("normal", "alert")
    # Vérifie le calcul : avg3m = (-9000 + -10000 + -8000) // 3 = -9000
    assert row.avg3m_cents == -9000
    assert row.current_cents == -29000
    assert row.delta_pct == round((-29000 - (-9000)) / abs(-9000) * 100, 2)


def test_drift_guard_insufficient_sorts_to_bottom(db_session: Session):
    """Les lignes 'insufficient' doivent apparaître après les 'alert'/'normal'."""
    e, ba = _mk_entity_with_ba(db_session, "GuardSortCo")
    cat_normal = _get_or_create_category(db_session, "cat-normal-sort", "Cat Normal Sort")
    cat_insuf = _get_or_create_category(db_session, "cat-insuf-sort", "Cat Insuffisant Sort")

    today_first = date.today().replace(day=1)

    # Tx anchor
    _mk_tx(db_session, ba, amount=Decimal("-1"), op_date=date.today(), label="anchor", category_id=cat_normal.id)

    # cat_normal : 3 mois actifs, avg3m grand
    for i, amt in zip(range(1, 5), ["-500", "-200", "-200", "-200"]):
        _mk_tx(db_session, ba, amount=Decimal(amt), op_date=_add_months(today_first, -i), label=f"n-{i}", category_id=cat_normal.id)

    # cat_insuf : 1 seul mois actif
    _mk_tx(db_session, ba, amount=Decimal("-500"), op_date=_add_months(today_first, -1), label="i-cur", category_id=cat_insuf.id)
    _mk_tx(db_session, ba, amount=Decimal("-30"), op_date=_add_months(today_first, -4), label="i-prev", category_id=cat_insuf.id)

    result = compute_category_drift(db_session, entity_id=e.id, seuil_pct=30.0)

    statuses = [r.status for r in result.rows]
    # Tous les 'insufficient' après les autres
    first_insuf = next((i for i, s in enumerate(statuses) if s == "insufficient"), None)
    if first_insuf is not None:
        non_insuf_after = [s for s in statuses[first_insuf:] if s != "insufficient"]
        assert non_insuf_after == [], f"Des lignes non-insufficient apparaissent après 'insufficient': {statuses}"
