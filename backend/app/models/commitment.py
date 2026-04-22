"""Engagements (factures reçues/émises) à rapprocher avec les transactions."""
from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CommitmentDirection(str, enum.Enum):
    IN = "in"
    OUT = "out"


class CommitmentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"


class Commitment(Base):
    __tablename__ = "commitments"
    __table_args__ = (
        Index("ix_commitments_entity_status", "entity_id", "status"),
        Index("ix_commitments_expected_date", "expected_date"),
        Index("ix_commitments_matched_transaction_id", "matched_transaction_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    counterparty_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("counterparties.id", ondelete="SET NULL"), nullable=True
    )
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    bank_account_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("bank_accounts.id", ondelete="SET NULL"), nullable=True
    )
    direction: Mapped[CommitmentDirection] = mapped_column(
        SQLEnum(
            CommitmentDirection,
            name="commitment_direction",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[CommitmentStatus] = mapped_column(
        SQLEnum(
            CommitmentStatus,
            name="commitment_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=CommitmentStatus.PENDING,
        server_default=CommitmentStatus.PENDING.value,
    )
    matched_transaction_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )
    reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pdf_attachment_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("imports.id", ondelete="SET NULL"), nullable=True
    )
    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    counterparty: Mapped[Optional["object"]] = relationship(
        "Counterparty", lazy="joined", foreign_keys=[counterparty_id]
    )
    category: Mapped[Optional["object"]] = relationship(
        "Category", lazy="joined", foreign_keys=[category_id]
    )

    def __repr__(self) -> str:
        return (
            f"<Commitment(id={self.id}, entity_id={self.entity_id}, "
            f"direction={self.direction.value}, amount_cents={self.amount_cents}, "
            f"status={self.status.value})>"
        )
