from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.deps import COOKIE_NAME, get_current_user, require_admin
from app.models.user import User, UserRole
from app.security import encode_session_token


def _make_app(db_session: Session) -> FastAPI:
    test_app = FastAPI()

    def _override_db():
        yield db_session

    def _override_settings() -> Settings:
        return Settings(  # type: ignore[call-arg]
            database_url="postgresql+psycopg://x/x",
            secret_key="x" * 32,
            session_hours=1,
            cors_origins_raw="http://localhost",
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
    r = client.get("/protected", cookies={COOKIE_NAME: token})
    assert r.status_code == 200
    assert r.json() == {"email": "u@x.com"}


def test_reader_cannot_reach_admin_route(db_session: Session) -> None:
    user = User(email="r@x.com", password_hash="h", role=UserRole.READER)
    db_session.add(user)
    db_session.commit()

    app = _make_app(db_session)
    client = TestClient(app)
    token = encode_session_token(user_id=user.id, secret="x" * 32)
    r = client.get("/admin-only", cookies={COOKIE_NAME: token})
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
    r = client.get("/protected", cookies={COOKIE_NAME: token})
    assert r.status_code == 401
