"""Tests du modèle Transaction."""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.bank_account import BankAccount
from app.models.entity import Entity
from app.models.import_record import ImportRecord
from app.models.transaction import Transaction
from app.models.user import User, UserRole


def _seed(db_session):
    u = User(email="a@b.fr", password_hash="x", role=UserRole.ADMIN, full_name="A")
    e = Entity(name="Acreed", legal_name="Acreed SAS")
    db_session.add_all([u, e])
    db_session.commit()
    ba = BankAccount(entity_id=e.id, name="Delubac", iban="FR76",
                     bank_name="Delubac", bank_code="delubac")
    db_session.add(ba)
    db_session.commit()
    imp = ImportRecord(bank_account_id=ba.id, uploaded_by_id=u.id,
                       filename="f.pdf", file_size_bytes=1,
                       file_sha256="h" * 64, bank_code="delubac",
                       imported_count=0, duplicates_skipped=0)
    db_session.add(imp)
    db_session.commit()
    return u, ba, imp


def test_transaction_basic(db_session):
    u, ba, imp = _seed(db_session)
    t = Transaction(
        bank_account_id=ba.id,
        import_id=imp.id,
        operation_date=date(2026, 3, 5),
        value_date=date(2026, 3, 5),
        amount=Decimal("-80.00"),
        label="COTIS CARTE BUSI IMM",
        raw_label="COTIS CARTE BUSI IMM",
        dedup_key="a" * 64,
        statement_row_index=0,
    )
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    assert t.id is not None
    assert t.is_aggregation_parent is False
    assert t.is_intercompany is False
    assert t.created_at is not None


def test_transaction_dedup_key_unique(db_session):
    u, ba, imp = _seed(db_session)
    common = dict(bank_account_id=ba.id, import_id=imp.id,
                  operation_date=date(2026, 3, 5), value_date=date(2026, 3, 5),
                  amount=Decimal("-10.00"), label="L", raw_label="L",
                  dedup_key="d" * 64, statement_row_index=0)
    db_session.add(Transaction(**common))
    db_session.commit()
    db_session.add(Transaction(**{**common, "statement_row_index": 1}))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_transaction_parent_child(db_session):
    u, ba, imp = _seed(db_session)
    parent = Transaction(
        bank_account_id=ba.id, import_id=imp.id,
        operation_date=date(2026, 3, 6), value_date=date(2026, 3, 6),
        amount=Decimal("-1000.60"),
        label="VIR SEPA JEAN DUPONT",
        raw_label="VIR SEPA JEAN DUPONT",
        dedup_key="p" * 64, statement_row_index=0,
        is_aggregation_parent=True,
    )
    db_session.add(parent)
    db_session.commit()
    child = Transaction(
        bank_account_id=ba.id, import_id=imp.id,
        operation_date=date(2026, 3, 6), value_date=date(2026, 3, 6),
        amount=Decimal("-0.50"),
        label="COMMISSION VIR SEPA JEAN DUPONT",
        raw_label="COMMISSION VIR SEPA JEAN DUPONT",
        dedup_key="c" * 64, statement_row_index=1,
        parent_transaction_id=parent.id,
    )
    db_session.add(child)
    db_session.commit()
    db_session.refresh(child)
    assert child.parent_transaction_id == parent.id
