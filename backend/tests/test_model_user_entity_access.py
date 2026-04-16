import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.entity import Entity
from app.models.user import User, UserRole
from app.models.user_entity_access import UserEntityAccess


def test_link_user_to_entity(db_session: Session) -> None:
    user = User(email="u@x.com", password_hash="h", role=UserRole.READER)
    entity = Entity(name="E", legal_name="E SARL")
    db_session.add_all([user, entity])
    db_session.flush()

    link = UserEntityAccess(user_id=user.id, entity_id=entity.id)
    db_session.add(link)
    db_session.commit()

    assert link.user_id == user.id
    assert link.entity_id == entity.id


def test_uniqueness(db_session: Session) -> None:
    user = User(email="x@y.com", password_hash="h", role=UserRole.READER)
    entity = Entity(name="E2", legal_name="E2 SARL")
    db_session.add_all([user, entity])
    db_session.flush()

    db_session.add(UserEntityAccess(user_id=user.id, entity_id=entity.id))
    db_session.commit()

    db_session.add(UserEntityAccess(user_id=user.id, entity_id=entity.id))
    with pytest.raises(IntegrityError):
        db_session.commit()
