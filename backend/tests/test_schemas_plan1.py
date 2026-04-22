"""Sérialisation/désérialisation des schémas Plan 1."""
from datetime import date
from decimal import Decimal

from app.schemas.counterparty import CounterpartyRead, CounterpartyUpdate
from app.schemas.import_record import ImportRecordRead
from app.schemas.transaction import TransactionFilter, TransactionRead


def test_import_record_read_minimal() -> None:
    obj = ImportRecordRead(
        id=1,
        bank_account_id=1,
        bank_code="delubac",
        status="completed",
        filename="x.pdf",
        imported_count=3,
        duplicates_skipped=0,
        counterparties_pending_created=1,
        created_at=date(2026, 4, 16),
    )
    d = obj.model_dump()
    assert d["status"] == "completed"


def test_transaction_read_amount_is_string() -> None:
    obj = TransactionRead(
        id=1,
        operation_date=date(2026, 1, 10),
        value_date=date(2026, 1, 10),
        label="VIR SEPA",
        raw_label="VIR SEPA",
        amount=Decimal("-42.50"),
        is_aggregation_parent=False,
        counterparty=None,
        category=None,
        entity_id=1,
        entity_name="SAS Test",
    )
    d = obj.model_dump()
    assert d["amount"] == "-42.50"  # Decimal sérialisé en str pour précision


def test_transaction_filter_defaults() -> None:
    f = TransactionFilter()
    assert f.page == 1
    assert f.per_page == 50


def test_counterparty_update_accepts_status() -> None:
    obj = CounterpartyUpdate(status="active", name="ACME")
    assert obj.status == "active"
    # Also verify Read schema is importable
    assert CounterpartyRead is not None
