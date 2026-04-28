"""Modèle ORM pour `client_errors`.

Remontée automatique des erreurs côté frontend (JS, fetch, console.error).
Alimenté par l'endpoint POST /api/client-errors. Lu par GET /api/admin/client-errors.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ClientError(Base):
    __tablename__ = "client_errors"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('debug', 'info', 'warning', 'error', 'fatal')",
            name="ck_client_errors_severity",
        ),
        CheckConstraint(
            "source IN ('window.onerror', 'unhandledrejection', 'console.error', 'apifetch', 'manual')",
            name="ck_client_errors_source",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="error", index=True
    )
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    stack: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    context_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
