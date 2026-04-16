from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BankAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_id: int
    name: str
    iban: str
    bic: str | None
    bank_name: str
    bank_code: str
    account_number: str | None
    currency: str
    is_active: bool
    created_at: datetime


class BankAccountCreate(BaseModel):
    entity_id: int
    name: str = Field(min_length=1, max_length=255)
    iban: str = Field(min_length=14, max_length=34)
    bic: str | None = Field(default=None, max_length=11)
    bank_name: str = Field(min_length=1, max_length=255)
    bank_code: str = Field(min_length=1, max_length=50)
    account_number: str | None = Field(default=None, max_length=34)
    currency: str = Field(default="EUR", min_length=3, max_length=3)


class BankAccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    bic: str | None = Field(default=None, max_length=11)
    bank_name: str | None = Field(default=None, min_length=1, max_length=255)
    bank_code: str | None = Field(default=None, min_length=1, max_length=50)
    is_active: bool | None = None
