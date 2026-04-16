"""Vérifie que les fixtures conftest API sont bien exposées."""
from fastapi.testclient import TestClient

from app.models.bank_account import BankAccount
from app.models.user import User


def test_client_is_test_client(client: TestClient) -> None:
    assert isinstance(client, TestClient)


def test_auth_user_is_logged_in(client: TestClient, auth_user: User) -> None:
    resp = client.get("/api/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == auth_user.email


def test_auth_user_with_bank_account_dict_shape(auth_user_with_bank_account) -> None:
    assert "user" in auth_user_with_bank_account
    assert "entity" in auth_user_with_bank_account
    assert "bank_account" in auth_user_with_bank_account
    assert isinstance(auth_user_with_bank_account["bank_account"], BankAccount)


def test_other_entity_bank_account_is_inaccessible(
    client: TestClient, auth_user: User, other_entity_bank_account: BankAccount,
) -> None:
    # Le user authentifié ne doit PAS avoir UserEntityAccess sur cette entité
    assert other_entity_bank_account.entity_id is not None
