"""Transaction bancaire : table centrale du système."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if False:  # TYPE_CHECKING-like guard avoiding runtime import cycles
    from app.models.category import Category
    from app.models.counterparty import Counterparty


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_tx_operation_date", "operation_date"),
        Index("ix_tx_bank_account_date", "bank_account_id", "operation_date"),
        Index("ix_tx_category", "category_id"),
        Index("ix_tx_counterparty", "counterparty_id"),
        Index("uq_tx_dedup_key", "dedup_key", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bank_account_id: Mapped[int] = mapped_column(
        ForeignKey("bank_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    import_id: Mapped[int] = mapped_column(
        ForeignKey("imports.id", ondelete="RESTRICT"), nullable=False
    )
    parent_transaction_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    counterparty_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("counterparties.id", ondelete="SET NULL"), nullable=True
    )
    counter_entity_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("entities.id", ondelete="SET NULL"), nullable=True
    )

    operation_date: Mapped[date] = mapped_column(Date, nullable=False)
    value_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    label: Mapped[str] = mapped_column(String(500), nullable=False)
    raw_label: Mapped[str] = mapped_column(String(500), nullable=False)
    dedup_key: Mapped[str] = mapped_column(String(64), nullable=False)
    statement_row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_aggregation_parent: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    is_intercompany: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
        onupdate=func.now()
    )

    counterparty: Mapped[Optional["Counterparty"]] = relationship(
        "Counterparty", lazy="raise", foreign_keys=[counterparty_id]
    )
    category: Mapped[Optional["Category"]] = relationship(
        "Category", lazy="raise", foreign_keys=[category_id]
    )

    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, {self.operation_date}, {self.amount}€)>"
