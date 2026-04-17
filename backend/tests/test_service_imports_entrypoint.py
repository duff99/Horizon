from pathlib import Path
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.entity import Entity
from app.models.import_record import ImportStatus
from app.services.imports import import_pdf_bytes, FileTooLargeError

FIXTURES = Path(__file__).parent / "fixtures" / "delubac"


def _make_ba(session: Session) -> BankAccount:
    e = Entity(name="SAS Test", legal_name="SAS Test SARL")
    session.add(e)
    session.flush()
    ba = BankAccount(
        entity_id=e.id, bank_code="delubac", bank_name="Delubac",
        iban="FR7600000000000000000000001", name="Compte courant",
    )
    session.add(ba)
    session.flush()
    return ba


def test_import_pdf_bytes_happy_path(db_session: Session) -> None:
    ba = _make_ba(db_session)
    pdf = (FIXTURES / "synthetic_minimal.pdf").read_bytes()
    rec = import_pdf_bytes(
        db_session,
        bank_account_id=ba.id,
        pdf_bytes=pdf,
        filename="synthetic_minimal.pdf",
    )
    assert rec.status == ImportStatus.COMPLETED
    assert rec.imported_count >= 3
    assert rec.filename == "synthetic_minimal.pdf"
    assert rec.file_sha256 is not None


def test_import_pdf_bytes_rejects_oversized(db_session: Session) -> None:
    import pytest
    ba = _make_ba(db_session)
    big = b"%PDF-1.4\n" + b"x" * (21 * 1024 * 1024)
    with pytest.raises(FileTooLargeError):
        import_pdf_bytes(
            db_session,
            bank_account_id=ba.id,
            pdf_bytes=big,
            filename="big.pdf",
        )
