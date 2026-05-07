"""Tests du modèle ImportRecord."""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.bank_account import BankAccount
from app.models.entity import Entity
from app.models.import_record import ImportRecord, ImportStatus
from app.models.user import User, UserRole


def _seed(db_session) -> tuple[User, BankAccount]:
    u = User(email="a@b.fr", password_hash="x", role=UserRole.ADMIN)
    e = Entity(name="Acreed", legal_name="Acreed SAS")
    db_session.add_all([u, e])
    db_session.commit()
    ba = BankAccount(entity_id=e.id, name="Delubac pro", iban="FR7612345",
                     bank_name="Delubac", bank_code="delubac")
    db_session.add(ba)
    db_session.commit()
    return u, ba


def test_import_record_basic(db_session) -> None:
    u, ba = _seed(db_session)
    rec = ImportRecord(
        bank_account_id=ba.id,
        uploaded_by_id=u.id,
        filename="releve_mars.pdf",
        file_size_bytes=12345,
        file_sha256="a" * 64,
        bank_code="delubac",
        status=ImportStatus.COMPLETED,
        period_start=date(2026, 3, 1),
        period_end=date(2026, 3, 31),
        opening_balance=Decimal("1000.00"),
        closing_balance=Decimal("1500.00"),
        imported_count=42,
        duplicates_skipped=3,
        counterparties_pending_created=5,
    )
    db_session.add(rec)
    db_session.commit()
    db_session.refresh(rec)
    assert rec.id is not None
    assert rec.created_at is not None
    assert rec.imported_count == 42
    assert rec.status == ImportStatus.COMPLETED


def test_import_record_status_enum(db_session) -> None:
    u, ba = _seed(db_session)
    for st in (ImportStatus.PENDING, ImportStatus.COMPLETED, ImportStatus.FAILED):
        rec = ImportRecord(
            bank_account_id=ba.id, uploaded_by_id=u.id,
            filename=f"f_{st.value}.pdf", file_size_bytes=1,
            file_sha256=(st.value * 64)[:64],
            bank_code="delubac", status=st,
        )
        db_session.add(rec)
    db_session.commit()
    rows = db_session.query(ImportRecord).all()
    assert len(rows) == 3


def test_import_record_unique_per_account_sha(db_session) -> None:
    """Deux imports avec même (bank_account_id, file_sha256) doivent lever
    IntegrityError — contrainte uq_imports_account_sha256 (migration E2)."""
    u, ba = _seed(db_session)
    db_session.add(ImportRecord(
        bank_account_id=ba.id, uploaded_by_id=u.id,
        filename="f0.pdf", file_size_bytes=1,
        file_sha256="b" * 64, bank_code="delubac",
        status=ImportStatus.COMPLETED,
    ))
    db_session.commit()

    db_session.add(ImportRecord(
        bank_account_id=ba.id, uploaded_by_id=u.id,
        filename="f1.pdf", file_size_bytes=1,
        file_sha256="b" * 64, bank_code="delubac",
        status=ImportStatus.COMPLETED,
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_import_record_same_sha_different_accounts_allowed(db_session) -> None:
    """Deux comptes bancaires différents peuvent partager le même file_sha256 —
    l'index unique est partial sur (bank_account_id, file_sha256)."""
    u, ba1 = _seed(db_session)
    ba2 = BankAccount(entity_id=ba1.entity_id, name="Autre compte",
                      iban="FR7699999", bank_name="Autre", bank_code="autre")
    db_session.add(ba2)
    db_session.commit()

    for ba in (ba1, ba2):
        db_session.add(ImportRecord(
            bank_account_id=ba.id, uploaded_by_id=u.id,
            filename="releve.pdf", file_size_bytes=1,
            file_sha256="c" * 64, bank_code="delubac",
            status=ImportStatus.COMPLETED,
        ))
    db_session.commit()  # ne doit pas lever d'erreur

    rows = db_session.query(ImportRecord).filter_by(file_sha256="c" * 64).all()
    assert len(rows) == 2
