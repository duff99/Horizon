"""GET /api/imports et GET /api/imports/{id}."""
from pathlib import Path

from fastapi.testclient import TestClient

FIXTURES = Path(__file__).parent / "fixtures" / "delubac"


def test_list_imports_returns_user_accessible_imports(
    client: TestClient, auth_user_with_bank_account,
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    pdf = (FIXTURES / "synthetic_minimal.pdf").read_bytes()
    client.post(
        "/api/imports",
        data={"bank_account_id": str(ba.id)},
        files={"file": ("x.pdf", pdf, "application/pdf")},
    )

    resp = client.get("/api/imports")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 1
    assert body[0]["bank_code"] == "delubac"


def test_get_import_by_id_returns_detail(
    client: TestClient, auth_user_with_bank_account,
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    pdf = (FIXTURES / "synthetic_minimal.pdf").read_bytes()
    created = client.post(
        "/api/imports",
        data={"bank_account_id": str(ba.id)},
        files={"file": ("x.pdf", pdf, "application/pdf")},
    ).json()

    resp = client.get(f"/api/imports/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_import_404_when_not_found(client: TestClient, auth_user) -> None:
    resp = client.get("/api/imports/999999999")
    assert resp.status_code == 404
