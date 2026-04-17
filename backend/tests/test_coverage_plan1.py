"""Targeted tests to raise coverage of Plan 1 modules to ≥ 85 %.

Each test hits a specific uncovered branch rather than re-testing happy paths.
"""
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

FIXTURES = Path(__file__).parent / "fixtures" / "delubac"


# --- app/api/imports.py missing lines ---------------------------------------


def test_post_import_404_when_bank_account_missing(
    client: TestClient, auth_user_with_bank_account,
) -> None:
    """Line 37 : bank_account inexistant → 404."""
    resp = client.post(
        "/api/imports",
        data={"bank_account_id": "999999"},
        files={"file": ("x.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert resp.status_code == 404


def test_post_import_413_when_file_too_large(
    client: TestClient, auth_user_with_bank_account,
) -> None:
    """Lines 58-59 : FileTooLargeError → 413."""
    ba = auth_user_with_bank_account["bank_account"]
    pdf = (FIXTURES / "synthetic_minimal.pdf").read_bytes()
    with patch("app.api.imports.import_pdf_bytes") as m:
        from app.services.imports import FileTooLargeError

        m.side_effect = FileTooLargeError("trop gros")
        resp = client.post(
            "/api/imports",
            data={"bank_account_id": str(ba.id)},
            files={"file": ("x.pdf", pdf, "application/pdf")},
        )
    assert resp.status_code == 413


def test_post_import_422_when_too_many_pages(
    client: TestClient, auth_user_with_bank_account,
) -> None:
    """Lines 60-61 : TooManyPagesError → 422."""
    ba = auth_user_with_bank_account["bank_account"]
    pdf = (FIXTURES / "synthetic_minimal.pdf").read_bytes()
    with patch("app.api.imports.import_pdf_bytes") as m:
        from app.services.imports import TooManyPagesError

        m.side_effect = TooManyPagesError("trop de pages")
        resp = client.post(
            "/api/imports",
            data={"bank_account_id": str(ba.id)},
            files={"file": ("x.pdf", pdf, "application/pdf")},
        )
    assert resp.status_code == 422


def test_post_import_400_when_unknown_bank(
    client: TestClient, auth_user_with_bank_account,
) -> None:
    """Lines 62-66 : UnknownBankError → 400."""
    ba = auth_user_with_bank_account["bank_account"]
    pdf = (FIXTURES / "synthetic_minimal.pdf").read_bytes()
    with patch("app.api.imports.import_pdf_bytes") as m:
        from app.parsers.errors import UnknownBankError

        m.side_effect = UnknownBankError("banque inconnue")
        resp = client.post(
            "/api/imports",
            data={"bank_account_id": str(ba.id)},
            files={"file": ("x.pdf", pdf, "application/pdf")},
        )
    assert resp.status_code == 400


def test_post_import_422_when_parser_error(
    client: TestClient, auth_user_with_bank_account,
) -> None:
    """Lines 67-68 : ParserError générique → 422."""
    ba = auth_user_with_bank_account["bank_account"]
    pdf = (FIXTURES / "synthetic_minimal.pdf").read_bytes()
    with patch("app.api.imports.import_pdf_bytes") as m:
        from app.parsers.errors import ParserError

        m.side_effect = ParserError("ligne illisible")
        resp = client.post(
            "/api/imports",
            data={"bank_account_id": str(ba.id)},
            files={"file": ("x.pdf", pdf, "application/pdf")},
        )
    assert resp.status_code == 422


# --- app/api/transactions.py missing lines ----------------------------------


def test_list_transactions_filter_date_range_and_search(
    client: TestClient, auth_user_with_bank_account,
) -> None:
    """Lines 36-49 : date_from/date_to/search branches."""
    ba = auth_user_with_bank_account["bank_account"]
    pdf = (FIXTURES / "synthetic_full_month.pdf").read_bytes()
    client.post(
        "/api/imports",
        data={"bank_account_id": str(ba.id)},
        files={"file": ("x.pdf", pdf, "application/pdf")},
    )
    # date_from + date_to
    r = client.get(
        "/api/transactions",
        params={"date_from": "2026-03-10", "date_to": "2026-03-20", "per_page": 100},
    )
    assert r.status_code == 200
    # search (matches at least one VIR SEPA entry)
    r = client.get("/api/transactions", params={"search": "VIR SEPA", "per_page": 100})
    assert r.status_code == 200
    assert r.json()["total"] >= 1


def test_list_transactions_filter_by_counterparty(
    client: TestClient, auth_user_with_bank_account,
) -> None:
    """Line 40-41 : counterparty_id branch."""
    ba = auth_user_with_bank_account["bank_account"]
    pdf = (FIXTURES / "synthetic_full_month.pdf").read_bytes()
    client.post(
        "/api/imports",
        data={"bank_account_id": str(ba.id)},
        files={"file": ("x.pdf", pdf, "application/pdf")},
    )
    pending = client.get("/api/counterparties", params={"status": "pending"}).json()
    assert pending
    cp_id = pending[0]["id"]
    r = client.get(
        "/api/transactions", params={"counterparty_id": cp_id, "per_page": 100}
    )
    assert r.status_code == 200
