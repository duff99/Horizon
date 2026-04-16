"""Sanity check des fixtures Delubac synthétiques."""
import json
from pathlib import Path

import pdfplumber
import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "delubac"

PDF_GT_PAIRS = [
    ("synthetic_minimal.pdf", "synthetic_minimal.ground_truth.json"),
    ("synthetic_sepa_trio.pdf", "synthetic_sepa_trio.ground_truth.json"),
    ("synthetic_full_month.pdf", "synthetic_full_month.ground_truth.json"),
]


@pytest.mark.parametrize("pdf_name,gt_name", PDF_GT_PAIRS)
def test_fixture_pdf_readable(pdf_name: str, gt_name: str) -> None:
    pdf_path = FIXTURES / pdf_name
    gt_path = FIXTURES / gt_name
    assert pdf_path.exists(), f"PDF manquant: {pdf_path}. Lance build_fixtures.py."
    assert gt_path.exists(), f"Vérité terrain manquante: {gt_path}"

    with pdfplumber.open(pdf_path) as pdf:
        assert len(pdf.pages) >= 1
        assert pdf.pages[0].extract_text(), "PDF vide"

    gt = json.loads(gt_path.read_text(encoding="utf-8"))
    for required in ("bank_code", "iban", "transactions", "period_start", "period_end"):
        assert required in gt, f"{gt_name} manque la clé {required}"
    assert gt["bank_code"] == "delubac"
    assert len(gt["transactions"]) >= 1
