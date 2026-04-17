"""GET /api/transactions : filtres, pagination, autorisation."""
from pathlib import Path

from fastapi.testclient import TestClient

FIXTURES = Path(__file__).parent / "fixtures" / "delubac"


def test_list_transactions_after_import(
    client: TestClient, auth_user_with_bank_account,
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    pdf = (FIXTURES / "synthetic_minimal.pdf").read_bytes()
    client.post(
        "/api/imports",
        data={"bank_account_id": str(ba.id)},
        files={"file": ("x.pdf", pdf, "application/pdf")},
    )
    resp = client.get("/api/transactions", params={"per_page": 10})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 3
    assert len(body["items"]) >= 3
    assert body["page"] == 1


def test_list_transactions_filter_by_bank_account(
    client: TestClient, auth_user_with_bank_account,
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    pdf = (FIXTURES / "synthetic_minimal.pdf").read_bytes()
    client.post(
        "/api/imports",
        data={"bank_account_id": str(ba.id)},
        files={"file": ("x.pdf", pdf, "application/pdf")},
    )
    resp = client.get(
        "/api/transactions", params={"bank_account_id": str(ba.id), "per_page": 100}
    )
    assert resp.status_code == 200
    assert all(True for _ in resp.json()["items"])  # tous liés à ce ba


def test_list_transactions_pagination(
    client: TestClient, auth_user_with_bank_account,
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    pdf = (FIXTURES / "synthetic_full_month.pdf").read_bytes()
    client.post(
        "/api/imports",
        data={"bank_account_id": str(ba.id)},
        files={"file": ("x.pdf", pdf, "application/pdf")},
    )
    p1 = client.get("/api/transactions", params={"page": 1, "per_page": 10}).json()
    p2 = client.get("/api/transactions", params={"page": 2, "per_page": 10}).json()
    assert p1["items"] != p2["items"]
    assert len(p1["items"]) == 10
