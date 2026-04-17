"""GET /api/counterparties et PATCH /api/counterparties/{id}."""
from pathlib import Path

from fastapi.testclient import TestClient

FIXTURES = Path(__file__).parent / "fixtures" / "delubac"


def test_list_counterparties_includes_pending(
    client: TestClient, auth_user_with_bank_account,
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    pdf = (FIXTURES / "synthetic_minimal.pdf").read_bytes()
    client.post(
        "/api/imports",
        data={"bank_account_id": str(ba.id)},
        files={"file": ("x.pdf", pdf, "application/pdf")},
    )
    resp = client.get("/api/counterparties", params={"status": "pending"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_patch_counterparty_activates_it(
    client: TestClient, auth_user_with_bank_account,
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    pdf = (FIXTURES / "synthetic_minimal.pdf").read_bytes()
    client.post(
        "/api/imports",
        data={"bank_account_id": str(ba.id)},
        files={"file": ("x.pdf", pdf, "application/pdf")},
    )
    cp = client.get("/api/counterparties", params={"status": "pending"}).json()[0]
    resp = client.patch(
        f"/api/counterparties/{cp['id']}",
        json={"status": "active", "name": "ACME SAS Validé"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"
    assert resp.json()["name"] == "ACME SAS Validé"
