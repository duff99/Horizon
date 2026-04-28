"""Modèle ORM pour la table `backup_history`.

Tracé opérationnel des backups Postgres. Alimentée par `scripts/backup/backup-db.sh`
(insert au début avec status=running, update à la fin avec status=success/failed)
et par `scripts/backup/verify-restore.sh` (update verified_at).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    CHAR,
    CheckConstraint,
    DateTime,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BackupHistory(Base):
    __tablename__ = "backup_history"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'success', 'failed', 'verified')",
            name="ck_backup_history_status",
        ),
        CheckConstraint(
            "type IN ('scheduled', 'manual', 'pre-op', 'restore-test')",
            name="ck_backup_history_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    sha256: Mapped[Optional[str]] = mapped_column(CHAR(64), nullable=True)
    imports_size_bytes: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True
    )
    imports_sha256: Mapped[Optional[str]] = mapped_column(CHAR(64), nullable=True)
    row_counts_json: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_step: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<BackupHistory(id={self.id}, status={self.status!r}, "
            f"file_path={self.file_path!r})>"
        )
