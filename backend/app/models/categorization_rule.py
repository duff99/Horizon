"""Modèle CategorizationRule : règle de catégorisation automatique."""
from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer,
    Numeric, String, func, text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RuleLabelOperator(str, enum.Enum):
    CONTAINS = "CONTAINS"
    STARTS_WITH = "STARTS_WITH"
    ENDS_WITH = "ENDS_WITH"
    EQUALS = "EQUALS"


class RuleAmountOperator(str, enum.Enum):
    EQ = "EQ"
    NE = "NE"
    GT = "GT"
    LT = "LT"
    BETWEEN = "BETWEEN"


class RuleDirection(str, enum.Enum):
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"
    ANY = "ANY"


class CategorizationRule(Base):
    __tablename__ = "categorization_rules"
    __table_args__ = (
        Index(
            "uq_rule_priority_per_scope",
            text("COALESCE(entity_id, 0)"),
            "priority",
            unique=True,
        ),
        CheckConstraint(
            "(amount_operator IS NULL) OR (amount_value IS NOT NULL)",
            name="ck_rule_amount_value_required",
        ),
        CheckConstraint(
            "(amount_operator <> 'BETWEEN') OR "
            "(amount_value2 IS NOT NULL AND amount_value < amount_value2)",
            name="ck_rule_between_coherent",
        ),
        CheckConstraint(
            "(label_operator IS NULL) OR (label_value IS NOT NULL AND length(label_value) >= 1)",
            name="ck_rule_label_value_required",
        ),
        CheckConstraint(
            "("
            "  label_operator IS NOT NULL"
            "  OR counterparty_id IS NOT NULL"
            "  OR bank_account_id IS NOT NULL"
            "  OR amount_operator IS NOT NULL"
            "  OR direction <> 'ANY'"
            ")",
            name="ck_rule_at_least_one_filter",
        ),
        Index("ix_rule_entity_priority", "entity_id", "priority"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), nullable=True
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    label_operator: Mapped[Optional[RuleLabelOperator]] = mapped_column(
        Enum(RuleLabelOperator, name="rule_label_operator"), nullable=True
    )
    label_value: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    direction: Mapped[RuleDirection] = mapped_column(
        Enum(RuleDirection, name="rule_direction"),
        nullable=False, default=RuleDirection.ANY,
    )
    amount_operator: Mapped[Optional[RuleAmountOperator]] = mapped_column(
        Enum(RuleAmountOperator, name="rule_amount_operator"), nullable=True
    )
    amount_value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    amount_value2: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    counterparty_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("counterparties.id", ondelete="SET NULL"), nullable=True
    )
    bank_account_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("bank_accounts.id", ondelete="SET NULL"), nullable=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False
    )
    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        scope = f"entity={self.entity_id}" if self.entity_id else "global"
        return f"<CategorizationRule(id={self.id}, {scope}, prio={self.priority}, {self.name!r})>"
