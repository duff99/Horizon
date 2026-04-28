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
    type: str
    file_path: str
    size_bytes: int | None
    sha256: str | None
    imports_size_bytes: int | None
    imports_sha256: str | None
    row_counts_json: dict[str, Any] | None
    error_message: str | None
    error_step: str | None
    verified_at: datetime | None
    created_at: datetime


class BackupTriggerRequest(BaseModel):
    """Type d'opération demandée depuis la page UI Sauvegardes."""

    type: str  # 'manual' ou 'restore-test'


class BackupTriggerResponse(BaseModel):
    row_id: uuid.UUID


class BackupDiskStats(BaseModel):
    mount: str
    size_gb: int
    used_gb: int
    avail_gb: int
    used_pct: int
    threshold_pct: int
    status: str  # 'ok' ou 'alert'
