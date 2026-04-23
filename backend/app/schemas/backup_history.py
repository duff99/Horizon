"""Schémas Pydantic pour l'endpoint admin de lecture `backup_history`."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class BackupHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    started_at: datetime
    completed_at: datetime | None
    status: str
    file_path: str
    size_bytes: int | None
    sha256: str | None
    row_counts_json: dict[str, Any] | None
    error_message: str | None
    verified_at: datetime | None
    created_at: datetime
