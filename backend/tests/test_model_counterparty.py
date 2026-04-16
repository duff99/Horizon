"""Tests du modèle Counterparty."""
import pytest
from sqlalchemy.exc import IntegrityError

from app.models.counterparty import Counterparty, CounterpartyStatus
from app.models.entity import Entity


def _mk_entity(session, name="SAS Test") -> Entity:
    e = Entity(name=name, legal_name=f"{name} SA")
    session.add(e)
    session.flush()
    return e


def test_counterparty_basic(db_session) -> None:
    e = _mk_entity(db_session)
    cp = Counterparty(entity_id=e.id, name="URSSAF", normalized_name="URSSAF",
                      status=CounterpartyStatus.PENDING)
    db_session.add(cp)
    db_session.commit()
    db_session.refresh(cp)
    assert cp.id is not None
    assert cp.status == CounterpartyStatus.PENDING
    assert cp.created_at is not None


def test_counterparty_status_enum(db_session) -> None:
    e = _mk_entity(db_session)
    for st in (CounterpartyStatus.PENDING,
               CounterpartyStatus.ACTIVE,
               CounterpartyStatus.IGNORED):
        db_session.add(Counterparty(entity_id=e.id, name=f"n_{st.value}",
                                    normalized_name=f"N {st.value}",
                                    status=st))
    db_session.commit()
    rows = db_session.query(Counterparty).all()
    assert len(rows) == 3


def test_counterparty_normalized_name_unique_per_entity(db_session) -> None:
    e = _mk_entity(db_session)
    db_session.add(Counterparty(entity_id=e.id, name="URSSAF Paris",
                                normalized_name="URSSAF",
                                status=CounterpartyStatus.ACTIVE))
    db_session.commit()
    db_session.add(Counterparty(entity_id=e.id, name="Urssaf Lyon",
                                normalized_name="URSSAF",
                                status=CounterpartyStatus.PENDING))
    with pytest.raises(IntegrityError):
        db_session.commit()
