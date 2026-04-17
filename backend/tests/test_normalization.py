"""Tests des helpers de normalisation."""
from datetime import date
from decimal import Decimal

import pytest

from app.parsers.normalization import (
    compute_dedup_key,
    extract_counterparty,
    fr_amount_to_decimal,
    fr_date_to_date,
    fix_latin1_encoding,
    normalize_label,
)


@pytest.mark.parametrize("raw,expected", [
    ("1.234,56", Decimal("1234.56")),
    ("0,10", Decimal("0.10")),
    ("25.204,95", Decimal("25204.95")),
    ("92,32", Decimal("92.32")),
    ("0", Decimal("0")),
])
def test_fr_amount_to_decimal(raw: str, expected: Decimal) -> None:
    assert fr_amount_to_decimal(raw) == expected


def test_fr_amount_invalid_raises() -> None:
    with pytest.raises(ValueError):
        fr_amount_to_decimal("abc")


def test_fr_date_to_date_basic() -> None:
    assert fr_date_to_date("02/03/2026") == date(2026, 3, 2)


def test_fr_date_invalid_raises() -> None:
    with pytest.raises(ValueError):
        fr_date_to_date("32/13/2026")


@pytest.mark.parametrize("raw,expected", [
    ("  Intérêts  de   retard  ", "INTERETS DE RETARD"),
    ("COMMISSION\nVIR\tSEPA", "COMMISSION VIR SEPA"),
    ("Créance n° 0502321", "CREANCE N 0502321"),
])
def test_normalize_label(raw: str, expected: str) -> None:
    assert normalize_label(raw) == expected


def test_fix_latin1_encoding_passthrough() -> None:
    # Texte déjà correct : pas de changement
    assert fix_latin1_encoding("Intérêts de retard") == "Intérêts de retard"


def test_fix_latin1_encoding_fixes_mojibake() -> None:
    # Cas réel Delubac : "Intérêts" mal décodé devient "IntÃ©rÃªts"
    assert fix_latin1_encoding("IntÃ©rÃªts de retard") == "Intérêts de retard"


def test_extract_counterparty_vir_sepa() -> None:
    assert extract_counterparty("VIR SEPA NIZAR MOUADDEB") == "NIZAR MOUADDEB"
    assert extract_counterparty("VIR SEPA BNP PARIBAS FACTOR") == "BNP PARIBAS FACTOR"
    assert extract_counterparty("VIR SEPA JEAN-PAUL DUPONT") == "JEAN-PAUL DUPONT"


def test_extract_counterparty_prlv_sepa() -> None:
    assert extract_counterparty("PRLV SEPA URSSAF") == "URSSAF"
    assert extract_counterparty("PRLV SEPA DGFIP") == "DGFIP"


def test_extract_counterparty_carte() -> None:
    assert extract_counterparty("CARTE 25/03 SAS LE BACCHUS") == "SAS LE BACCHUS"
    assert extract_counterparty("CARTE 26/03 EDF ENTREPRISE") == "EDF ENTREPRISE"


def test_extract_counterparty_commission_vir_sepa() -> None:
    # Les lignes COMMISSION / TVA se réfèrent à la contrepartie de leur parent
    assert extract_counterparty("COMMISSION VIR SEPA NIZAR MOUADDEB") == "NIZAR MOUADDEB"
    assert extract_counterparty("TVA VIR SEPA NIZAR MOUADDEB") == "NIZAR MOUADDEB"


def test_extract_counterparty_unknown_returns_none() -> None:
    assert extract_counterparty("ARRETE DE COMPTE AU 28/02/26") is None
    assert extract_counterparty("Intérêts de retard") is None


def test_compute_dedup_key_stable() -> None:
    k1 = compute_dedup_key(bank_account_id=1, operation_date=date(2026, 3, 1),
                           value_date=date(2026, 3, 1), amount=Decimal("-80.00"),
                           normalized_label="COTIS CARTE", statement_row_index=0)
    k2 = compute_dedup_key(bank_account_id=1, operation_date=date(2026, 3, 1),
                           value_date=date(2026, 3, 1), amount=Decimal("-80.00"),
                           normalized_label="COTIS CARTE", statement_row_index=0)
    assert k1 == k2
    assert len(k1) == 64


def test_compute_dedup_key_differs_on_row_index() -> None:
    args = dict(bank_account_id=1, operation_date=date(2026, 3, 1),
                value_date=date(2026, 3, 1), amount=Decimal("-80.00"),
                normalized_label="COTIS CARTE")
    assert compute_dedup_key(**args, statement_row_index=0) \
        != compute_dedup_key(**args, statement_row_index=1)
