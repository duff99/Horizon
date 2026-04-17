from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CounterpartyNested(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    status: str


class CategoryNested(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    operation_date: date
    value_date: date
    label: str
    raw_label: str
    amount: Decimal
    is_aggregation_parent: bool = False
    parent_transaction_id: int | None = None
    counterparty: CounterpartyNested | None = None
    category: CategoryNested | None = None

    def model_dump(self, **kw):
        d = super().model_dump(**kw)
        # Decimal → str pour conserver la précision côté client
        if isinstance(d.get("amount"), Decimal):
            d["amount"] = str(d["amount"])
        return d


class TransactionFilter(BaseModel):
    bank_account_id: int | None = None
    date_from: date | None = None
    date_to: date | None = None
    counterparty_id: int | None = None
    search: str | None = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=50, ge=1, le=500)


class TransactionListResponse(BaseModel):
    items: list[TransactionRead]
    total: int
    page: int
    per_page: int
