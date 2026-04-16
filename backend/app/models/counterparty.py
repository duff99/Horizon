"""Contrepartie (fournisseur, client, salarié) associée à des transactions."""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CounterpartyStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    IGNORED = "ignored"


class Counterparty(Base):
    __tablename__ = "counterparties"
    __table_args__ = (
        UniqueConstraint("entity_id", "normalized_name",
                         name="uq_counterparties_entity_normalized"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    status: Mapped[CounterpartyStatus] = mapped_column(
        Enum(CounterpartyStatus,
             name="counterparty_status",
             values_callable=lambda e: [m.value for m in e]),
        nullable=False, default=CounterpartyStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Counterparty(id={self.id}, entity_id={self.entity_id}, name={self.name!r}, status={self.status.value})>"
