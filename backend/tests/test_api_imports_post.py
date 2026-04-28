"""POST /api/imports : upload PDF et création d'un ImportRecord."""
from pathlib import Path

from fastapi.testclient import TestClient

FIXTURES = Path(__file__).parent / "fixtures" / "delubac"


def test_post_import_returns_201_and_record(
    client: TestClient, auth_user_with_bank_account,
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    pdf = (FIXTURES / "synthetic_minimal.pdf").read_bytes()
    resp = client.post(
        "/api/imports",
        data={"bank_account_id": str(ba.id)},
        files={"file": ("synthetic_minimal.pdf", pdf, "application/pdf")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "completed"
    assert body["imported_count"] >= 3


def test_post_import_rejects_non_pdf(
    client: TestClient, auth_user_with_bank_account,
) -> None:
    ba = auth_user_with_bank_account["bank_account"]
    resp = client.post(
        "/api/imports",
        data={"bank_account_id": str(ba.id)},
        files={"file": ("fake.pdf", b"not a pdf", "application/pdf")},
    )
    assert resp.status_code == 400
    assert "pdf" in resp.json()["detail"].lower()


def test_post_import_forbidden_without_access(
    client: TestClient, auth_user_reader, other_entity_bank_account,
) -> None:
    resp = client.post(
        "/api/imports",
        data={"bank_account_id": str(other_entity_bank_account.id)},
        files={"file": ("x.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert resp.status_code == 403
