"""Schémas Pydantic pour l'endpoint admin de lecture `audit_log`."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    occurred_at: datetime
    user_id: int | None
    user_email: str | None
    action: str
    entity_type: str
    entity_id: str
    before_json: dict[str, Any] | None
    after_json: dict[str, Any] | None
    diff_json: dict[str, Any] | None
    ip_address: str | None
    user_agent: str | None
    request_id: str | None


class AuditLogListResponse(BaseModel):
    items: list[AuditLogRead]
    total: int
    limit: int
    offset: int
