import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.deps import (
    COOKIE_NAME,
    accessible_entity_ids_subquery,
    get_current_user,
    require_admin,
    require_entity_access,
)
from app.models.entity import Entity
from app.models.user import User, UserRole
from app.models.user_entity_access import UserEntityAccess
from app.security import encode_session_token


def _make_app(db_session: Session) -> FastAPI:
    test_app = FastAPI()

    def _override_db():
        yield db_session

    def _override_settings() -> Settings:
        return Settings(  # type: ignore[call-arg]
            DATABASE_URL="postgresql+psycopg://x/x",
            BACKEND_SECRET_KEY="x" * 32,
            BACKEND_SESSION_HOURS=1,
            BACKEND_CORS_ORIGINS="http://localhost",
        )

    test_app.dependency_overrides[get_db] = _override_db
    test_app.dependency_overrides[get_settings] = _override_settings

    @test_app.get("/protected")
    def protected(current: User = Depends(get_current_user)) -> dict[str, str]:
        return {"email": current.email}

    @test_app.get("/admin-only")
    def admin_only(current: User = Depends(require_admin)) -> dict[str, str]:
        return {"email": current.email}

    return test_app


def test_requires_cookie(db_session: Session) -> None:
    app = _make_app(db_session)
    client = TestClient(app)
    r = client.get("/protected")
    assert r.status_code == 401


def test_valid_cookie_admits(db_session: Session) -> None:
    user = User(
        email="u@x.com", password_hash="h", role=UserRole.READER, full_name="U"
    )
    db_session.add(user)
    db_session.commit()

    app = _make_app(db_session)
    client = TestClient(app)
    token = encode_session_token(user_id=user.id, secret="x" * 32)
    client.cookies.set(COOKIE_NAME, token)
    r = client.get("/protected")
    assert r.status_code == 200
    assert r.json() == {"email": "u@x.com"}


def test_reader_cannot_reach_admin_route(db_session: Session) -> None:
    user = User(email="r@x.com", password_hash="h", role=UserRole.READER)
    db_session.add(user)
    db_session.commit()

    app = _make_app(db_session)
    client = TestClient(app)
    token = encode_session_token(user_id=user.id, secret="x" * 32)
    client.cookies.set(COOKIE_NAME, token)
    r = client.get("/admin-only")
    assert r.status_code == 403


def test_deactivated_user_rejected(db_session: Session) -> None:
    user = User(
        email="d@x.com", password_hash="h", role=UserRole.ADMIN, is_active=False
    )
    db_session.add(user)
    db_session.commit()

    app = _make_app(db_session)
    client = TestClient(app)
    token = encode_session_token(user_id=user.id, secret="x" * 32)
    client.cookies.set(COOKIE_NAME, token)
    r = client.get("/protected")
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# require_entity_access — admin bypass + reader filtering (option C, 2026-04)
# ---------------------------------------------------------------------------


def test_require_entity_access_admin_bypass(db_session: Session) -> None:
    """Un admin sans entrée user_entity_access a accès implicite à toutes les entités."""
    admin = User(email="a-bypass@x.com", password_hash="h", role=UserRole.ADMIN)
    entity = Entity(name="EntBypass", legal_name="EntBypass")
    db_session.add_all([admin, entity])
    db_session.commit()

    # Aucune ligne user_entity_access pour admin → doit passer quand même
    require_entity_access(session=db_session, user=admin, entity_id=entity.id)


def test_require_entity_access_reader_without_grant_blocked(db_session: Session) -> None:
    reader = User(email="r-block@x.com", password_hash="h", role=UserRole.READER)
    entity = Entity(name="EntBlock", legal_name="EntBlock")
    db_session.add_all([reader, entity])
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        require_entity_access(session=db_session, user=reader, entity_id=entity.id)
    assert exc.value.status_code == 403


def test_require_entity_access_reader_with_grant_passes(db_session: Session) -> None:
    reader = User(email="r-pass@x.com", password_hash="h", role=UserRole.READER)
    entity = Entity(name="EntPass", legal_name="EntPass")
    db_session.add_all([reader, entity])
    db_session.flush()
    db_session.add(UserEntityAccess(user_id=reader.id, entity_id=entity.id))
    db_session.commit()

    require_entity_access(session=db_session, user=reader, entity_id=entity.id)


def test_accessible_entity_ids_admin_returns_all(db_session: Session) -> None:
    admin = User(email="a-all@x.com", password_hash="h", role=UserRole.ADMIN)
    e1 = Entity(name="A-all-1", legal_name="A-all-1")
    e2 = Entity(name="A-all-2", legal_name="A-all-2")
    db_session.add_all([admin, e1, e2])
    db_session.commit()

    sq = accessible_entity_ids_subquery(session=db_session, user=admin)
    ids = list(db_session.scalars(sq))
    assert e1.id in ids
    assert e2.id in ids


def test_accessible_entity_ids_reader_filtered(db_session: Session) -> None:
    reader = User(email="r-filter@x.com", password_hash="h", role=UserRole.READER)
    e1 = Entity(name="R-filter-1", legal_name="R-filter-1")
    e2 = Entity(name="R-filter-2", legal_name="R-filter-2")
    db_session.add_all([reader, e1, e2])
    db_session.flush()
    db_session.add(UserEntityAccess(user_id=reader.id, entity_id=e1.id))
    db_session.commit()

    sq = accessible_entity_ids_subquery(session=db_session, user=reader)
    ids = list(db_session.scalars(sq))
    assert e1.id in ids
    assert e2.id not in ids
