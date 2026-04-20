from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ImportRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bank_account_id: int
    bank_code: str
    status: Literal["pending", "completed", "failed"]
    filename: str | None = None
    file_sha256: str | None = None
    imported_count: int = 0
    duplicates_skipped: int = 0
    counterparties_pending_created: int = 0
    period_start: date | None = None
    period_end: date | None = None
    opening_balance: Decimal | None = None
    closing_balance: Decimal | None = None
    error_message: str | None = None
    created_at: date | datetime | None = None
