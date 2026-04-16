from datetime import UTC

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User, UserRole


def test_create_user(db_session: Session) -> None:
    user = User(
        email="admin@test.local",
        password_hash="fakehash",
        role=UserRole.ADMIN,
        full_name="Admin Test",
    )
    db_session.add(user)
    db_session.commit()

    assert user.id is not None
    assert user.is_active is True
    assert user.created_at is not None
    assert user.created_at.tzinfo == UTC


def test_email_is_unique(db_session: Session) -> None:
    u1 = User(email="a@b.com", password_hash="x", role=UserRole.READER)
    db_session.add(u1)
    db_session.commit()

    u2 = User(email="a@b.com", password_hash="y", role=UserRole.READER)
    db_session.add(u2)
    with pytest.raises(IntegrityError):
        db_session.commit()
