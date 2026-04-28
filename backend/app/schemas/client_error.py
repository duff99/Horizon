"""Schémas Pydantic pour les endpoints `/api/client-errors`."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# Sources doivent être en sync avec la check constraint SQL
ClientErrorSource = Literal[
    "window.onerror",
    "unhandledrejection",
    "console.error",
    "apifetch",
    "manual",
]
ClientErrorSeverity = Literal["debug", "info", "warning", "error", "fatal"]


class ClientErrorCreate(BaseModel):
    """Payload posté par le frontend.

    Champs limités en taille pour éviter qu'un payload gigantesque ne sature
    la DB ou ne devienne un vecteur d'abus (l'endpoint est rate-limité).
    """

    severity: ClientErrorSeverity = "error"
    source: ClientErrorSource
    message: str = Field(..., min_length=1, max_length=4000)
    stack: str | None = Field(default=None, max_length=20000)
    url: str | None = Field(default=None, max_length=2000)
    user_agent: str | None = Field(default=None, max_length=500)
    request_id: str | None = Field(default=None, max_length=64)
    context_json: dict[str, Any] | None = None


class ClientErrorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    occurred_at: datetime
    user_id: int | None
    user_email: str | None = None  # Joint depuis users.email pour confort UI
    severity: str
    source: str
    message: str
    stack: str | None
    url: str | None
    user_agent: str | None
    request_id: str | None
    context_json: dict[str, Any] | None


class ClientErrorListResponse(BaseModel):
    items: list[ClientErrorRead]
    total: int
    limit: int
    offset: int
