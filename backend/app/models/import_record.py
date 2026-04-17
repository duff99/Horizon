"""Journal des imports de relevés bancaires."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Optional

from sqlalchemy import (
    BigInteger, Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ImportStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class ImportRecord(Base):
    __tablename__ = "imports"

    id: Mapped[int] = mapped_column(primary_key=True)
    bank_account_id: Mapped[int] = mapped_column(
        ForeignKey("bank_accounts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    uploaded_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    file_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    bank_code: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[ImportStatus] = mapped_column(
        Enum(ImportStatus, name="import_status",
             values_callable=lambda e: [m.value for m in e]),
        nullable=False, default=ImportStatus.PENDING
    )
    period_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    period_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    opening_balance: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    closing_balance: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    imported_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicates_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    counterparties_pending_created: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    override_duplicates: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    audit: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<ImportRecord(id={self.id}, file={self.filename!r}, status={self.status.value}, nb={self.imported_count})>"
