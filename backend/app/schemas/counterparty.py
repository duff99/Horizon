from typing import Literal

from pydantic import BaseModel, ConfigDict


class CounterpartyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    entity_id: int
    name: str
    status: Literal["pending", "active", "ignored"]


class CounterpartyUpdate(BaseModel):
    status: Literal["active", "ignored"] | None = None
    name: str | None = None
