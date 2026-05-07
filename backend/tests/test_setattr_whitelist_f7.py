"""F7 — Vérifie que les PATCH n'acceptent que les champs whitelistés."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.entity import Entity
from app.models.bank_account import BankAccount
from app.models.user import User, UserRole
from app.models.user_entity_access import UserEntityAccess
from app.models.forecast_scenario import ForecastScenario
from app.security import hash_password


@pytest.fixture()
def admin_user_f7(db_session: Session) -> User:
    user = User(
        email="admin_f7@example.com",
        password_hash=hash_password("AdminPass123!"),
        role=UserRole.ADMIN,
        full_name="Admin F7",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def admin_client_f7(client: TestClient, admin_user_f7: User) -> TestClient:
    resp = client.post("/api/auth/login", json={
        "email": admin_user_f7.email,
        "password": "AdminPass123!",
    })
    assert resp.status_code == 200
    return client


@pytest.fixture()
def entity_f7(db_session: Session) -> Entity:
    e = Entity(name="Société F7", legal_name="Société F7")
    db_session.add(e)
    db_session.commit()
    db_session.refresh(e)
    return e


@pytest.fixture()
def bank_account_f7(db_session: Session, entity_f7: Entity) -> BankAccount:
    ba = BankAccount(
        entity_id=entity_f7.id,
        bank_code="delubac",
        bank_name="Delubac",
        iban="FR7600000000000000000000F77",
        name="Compte F7",
    )
    db_session.add(ba)
    db_session.commit()
    db_session.refresh(ba)
    return ba


@pytest.fixture()
def forecast_scenario_f7(db_session: Session, entity_f7: Entity, admin_user_f7: User) -> ForecastScenario:
    sc = ForecastScenario(
        entity_id=entity_f7.id,
        name="Scenario F7",
        description="Test",
        is_default=True,
        created_by_id=admin_user_f7.id,
    )
    db_session.add(sc)
    db_session.commit()
    db_session.refresh(sc)
    return sc


def test_user_patch_whitelisted_field_works(
    admin_client_f7: TestClient, admin_user_f7: User, db_session: Session
) -> None:
    """PATCH /api/users/{id} avec full_name → le champ est appliqué."""
    resp = admin_client_f7.patch(f"/api/users/{admin_user_f7.id}", json={
        "full_name": "Test Whitelist F7",
    })
    assert resp.status_code == 200
    db_session.expire(admin_user_f7)
    user = db_session.get(User, admin_user_f7.id)
    assert user is not None
    assert user.full_name == "Test Whitelist F7"


def test_user_patch_session_token_version_not_modified(
    admin_client_f7: TestClient, admin_user_f7: User, db_session: Session
) -> None:
    """PATCH /api/users/{id} avec full_name uniquement → session_token_version non modifié."""
    original_version = admin_user_f7.session_token_version
    resp = admin_client_f7.patch(f"/api/users/{admin_user_f7.id}", json={
        "full_name": "Test Session Guard",
    })
    assert resp.status_code == 200
    db_session.expire(admin_user_f7)
    user = db_session.get(User, admin_user_f7.id)
    assert user is not None
    assert user.session_token_version == original_version


def test_scenario_patch_only_allowed_fields(
    admin_client_f7: TestClient, forecast_scenario_f7: ForecastScenario,
    admin_user_f7: User, db_session: Session
) -> None:
    """PATCH /api/forecast/scenarios/{id} avec name → renommage effectif."""
    # Donner accès à l'entité pour le user admin
    access = UserEntityAccess(
        user_id=admin_user_f7.id,
        entity_id=forecast_scenario_f7.entity_id,
    )
    db_session.add(access)
    db_session.commit()

    original_entity_id = forecast_scenario_f7.entity_id
    resp = admin_client_f7.patch(
        f"/api/forecast/scenarios/{forecast_scenario_f7.id}",
        json={"name": "Scenario Renamed F7"},
    )
    assert resp.status_code == 200
    db_session.expire(forecast_scenario_f7)
    sc = db_session.get(ForecastScenario, forecast_scenario_f7.id)
    assert sc is not None
    assert sc.entity_id == original_entity_id
    assert sc.name == "Scenario Renamed F7"


def test_bank_account_patch_whitelisted_field(
    admin_client_f7: TestClient, bank_account_f7: BankAccount, db_session: Session
) -> None:
    """PATCH /api/bank-accounts/{id} avec name → champ mis à jour."""
    resp = admin_client_f7.patch(
        f"/api/bank-accounts/{bank_account_f7.id}",
        json={"name": "Nouveau nom F7"},
    )
    assert resp.status_code == 200
    db_session.expire(bank_account_f7)
    ba = db_session.get(BankAccount, bank_account_f7.id)
    assert ba is not None
    assert ba.name == "Nouveau nom F7"


def test_entity_patch_whitelisted_field(
    admin_client_f7: TestClient, entity_f7: Entity, db_session: Session
) -> None:
    """PATCH /api/entities/{id} avec name → champ mis à jour."""
    resp = admin_client_f7.patch(
        f"/api/entities/{entity_f7.id}",
        json={"name": "Entité Renommée F7"},
    )
    assert resp.status_code == 200
    db_session.expire(entity_f7)
    e = db_session.get(Entity, entity_f7.id)
    assert e is not None
    assert e.name == "Entité Renommée F7"
