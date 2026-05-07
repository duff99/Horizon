"""F5 — Tests pagination sur les listings non bornés."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.security import hash_password


@pytest.fixture()
def admin_user_f5(db_session: Session) -> User:
    user = User(
        email="admin_f5@example.com",
        password_hash=hash_password("AdminPass123!"),
        role=UserRole.ADMIN,
        full_name="Admin F5",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def admin_client_f5(client: TestClient, admin_user_f5: User) -> TestClient:
    resp = client.post("/api/auth/login", json={
        "email": admin_user_f5.email,
        "password": "AdminPass123!",
    })
    assert resp.status_code == 200
    return client


def test_counterparties_limit_param(admin_client_f5: TestClient) -> None:
    """GET /api/counterparties?limit=5&offset=0 → accepté."""
    resp = admin_client_f5.get("/api/counterparties?limit=5&offset=0")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_counterparties_limit_over_1000_rejected(admin_client_f5: TestClient) -> None:
    """GET /api/counterparties?limit=1001 → 422 (limit > 1000 interdit)."""
    resp = admin_client_f5.get("/api/counterparties?limit=1001")
    assert resp.status_code == 422


def test_counterparties_default_limit_is_array(admin_client_f5: TestClient) -> None:
    """GET /api/counterparties sans params → retourne un tableau (pas un wrapper)."""
    resp = admin_client_f5.get("/api/counterparties")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_rules_limit_param(admin_client_f5: TestClient) -> None:
    """GET /api/rules?limit=10&offset=0 → accepté."""
    resp = admin_client_f5.get("/api/rules?limit=10&offset=0")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_rules_limit_over_1000_rejected(admin_client_f5: TestClient) -> None:
    """GET /api/rules?limit=1001 → 422."""
    resp = admin_client_f5.get("/api/rules?limit=1001")
    assert resp.status_code == 422


def test_forecast_scenarios_limit_param(admin_client_f5: TestClient) -> None:
    """GET /api/forecast/scenarios?limit=10 → accepté."""
    resp = admin_client_f5.get("/api/forecast/scenarios?limit=10")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_forecast_scenarios_limit_over_1000_rejected(admin_client_f5: TestClient) -> None:
    """GET /api/forecast/scenarios?limit=1001 → 422."""
    resp = admin_client_f5.get("/api/forecast/scenarios?limit=1001")
    assert resp.status_code == 422


def test_forecast_lines_limit_requires_scenario_id(admin_client_f5: TestClient) -> None:
    """GET /api/forecast/lines sans scenario_id → 422 (paramètre obligatoire)."""
    resp = admin_client_f5.get("/api/forecast/lines?limit=10")
    assert resp.status_code == 422
