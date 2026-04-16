from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EntityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    legal_name: str
    siret: str | None
    parent_entity_id: int | None
    created_at: datetime


class EntityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    legal_name: str = Field(min_length=1, max_length=255)
    siret: str | None = Field(default=None, max_length=32)
    parent_entity_id: int | None = None


class EntityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    legal_name: str | None = Field(default=None, min_length=1, max_length=255)
    siret: str | None = Field(default=None, max_length=32)
    parent_entity_id: int | None = None
