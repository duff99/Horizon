"""Modèle ORM pour la table `audit_log`.

Audit trail finance-grade : chaque mutation sur une entité critique insère
une ligne ici. Alimenté par `app.services.audit.record_audit`.
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
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        CheckConstraint(
            "action IN ('create', 'update', 'delete')",
            name="ck_audit_log_action",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(60), nullable=False)
    before_json: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )
    after_json: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )
    diff_json: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, action={self.action!r}, "
            f"entity_type={self.entity_type!r}, entity_id={self.entity_id!r})>"
        )
