from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict


class CounterpartyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    entity_id: int
    name: str
    status: Literal["pending", "active", "ignored"]


class CounterpartyWithAggregates(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    entity_id: int
    name: str
    status: Literal["pending", "active", "ignored"]
    transaction_count: int
    volume_cumulated: float
    last_operation_date: date | None
    pending_commitment_count: int


class CounterpartyUpdate(BaseModel):
    status: Literal["active", "ignored"] | None = None
    name: str | None = None


class CounterpartyCreate(BaseModel):
    entity_id: int
    name: str
