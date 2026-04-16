import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.entity import Entity


def test_create_bank_account(db_session: Session) -> None:
    e = Entity(name="Filiale", legal_name="FIL SAS")
    db_session.add(e)
    db_session.flush()

    ba = BankAccount(
        entity_id=e.id,
        name="Compte pro Delubac",
        iban="FR7612879000011117020200105",
        bank_name="Delubac",
        bank_code="delubac",
        currency="EUR",
    )
    db_session.add(ba)
    db_session.commit()
    assert ba.id is not None
    assert ba.is_active is True


def test_iban_unique(db_session: Session) -> None:
    e = Entity(name="E3", legal_name="E3 SAS")
    db_session.add(e)
    db_session.flush()

    db_session.add(
        BankAccount(
            entity_id=e.id,
            name="A",
            iban="FR7612879000011117020200105",
            bank_name="Delubac",
            bank_code="delubac",
        )
    )
    db_session.commit()

    db_session.add(
        BankAccount(
            entity_id=e.id,
            name="B",
            iban="FR7612879000011117020200105",
            bank_name="Delubac",
            bank_code="delubac",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
