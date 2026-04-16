import pytest
from sqlalchemy.orm import Session

from app.models.entity import Entity, validate_entity_tree


def test_entity_without_parent(db_session: Session) -> None:
    holding = Entity(name="Holding", legal_name="HOLDING SARL", parent_entity_id=None)
    db_session.add(holding)
    db_session.commit()
    assert holding.id is not None
    assert holding.parent_entity_id is None


def test_entity_with_parent(db_session: Session) -> None:
    holding = Entity(name="Holding", legal_name="HOLDING SARL")
    db_session.add(holding)
    db_session.flush()

    filiale = Entity(name="Filiale 1", legal_name="FIL 1 SAS", parent_entity_id=holding.id)
    db_session.add(filiale)
    db_session.commit()

    assert filiale.parent_entity_id == holding.id


def test_entity_self_reference_forbidden(db_session: Session) -> None:
    """Un noeud ne peut pas être son propre parent (invariant applicatif)."""
    e = Entity(name="X", legal_name="X", id=1, parent_entity_id=1)
    with pytest.raises(ValueError, match="ne peut pas être son propre parent"):
        validate_entity_tree(e)


def test_entity_cycle_forbidden(db_session: Session) -> None:
    """Deux entités qui se pointent l'une l'autre forment un cycle."""
    a = Entity(name="A", legal_name="A")
    b = Entity(name="B", legal_name="B")
    db_session.add_all([a, b])
    db_session.flush()

    # Mise en place d'un cycle A ← B, puis on essaie B ← A
    a.parent_entity_id = b.id
    db_session.flush()
    b.parent_entity_id = a.id
    with pytest.raises(ValueError, match="Cycle détecté"):
        validate_entity_tree(b, session=db_session)
