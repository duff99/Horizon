"""Tests du modèle ImportRecord."""
from datetime import date
from decimal import Decimal

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


def test_import_record_allows_reimport_same_sha(db_session) -> None:
    """Deux imports avec même hash et même compte : autorisés (réimport avec override)
    mais détectables via la colonne. Contrainte soft applicative, pas DB."""
    u, ba = _seed(db_session)
    for i in range(2):
        db_session.add(ImportRecord(
            bank_account_id=ba.id, uploaded_by_id=u.id,
            filename=f"f{i}.pdf", file_size_bytes=1,
            file_sha256="b" * 64, bank_code="delubac",
            status=ImportStatus.COMPLETED,
        ))
    db_session.commit()
    rows = db_session.query(ImportRecord).filter_by(file_sha256="b" * 64).all()
    assert len(rows) == 2
