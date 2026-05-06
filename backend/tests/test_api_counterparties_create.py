"""POST /api/counterparties création manuelle."""
from fastapi.testclient import TestClient


def test_create_counterparty_manual(
    client: TestClient, auth_user_with_bank_account,
) -> None:
    entity_id = auth_user_with_bank_account["bank_account"].entity_id
    resp = client.post(
        "/api/counterparties",
        json={"entity_id": entity_id, "name": "Manual Tier SAS"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Manual Tier SAS"
    assert body["status"] == "active"


def test_create_counterparty_rejects_duplicate_normalized_name(
    client: TestClient, auth_user_with_bank_account,
) -> None:
    entity_id = auth_user_with_bank_account["bank_account"].entity_id
    client.post(
        "/api/counterparties",
        json={"entity_id": entity_id, "name": "ACME SAS"},
    )
    resp = client.post(
        "/api/counterparties",
        json={"entity_id": entity_id, "name": "ACME S.A.S."},
    )
    assert resp.status_code == 409
