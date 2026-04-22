"""Règle de calcul prévisionnel par (scenario, catégorie)."""
from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ForecastLineMethod(str, enum.Enum):
    RECURRING_FIXED = "RECURRING_FIXED"
    AVG_3M = "AVG_3M"
    AVG_6M = "AVG_6M"
    AVG_12M = "AVG_12M"
    PREVIOUS_MONTH = "PREVIOUS_MONTH"
    SAME_MONTH_LAST_YEAR = "SAME_MONTH_LAST_YEAR"
    BASED_ON_CATEGORY = "BASED_ON_CATEGORY"
    FORMULA = "FORMULA"


class ForecastLine(Base):
    __tablename__ = "forecast_lines"
    __table_args__ = (
        UniqueConstraint(
            "scenario_id", "category_id", name="uq_forecast_line_scenario_category"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    scenario_id: Mapped[int] = mapped_column(
        ForeignKey("forecast_scenarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    method: Mapped[ForecastLineMethod] = mapped_column(
        SQLEnum(ForecastLineMethod, name="forecast_line_method"),
        nullable=False,
    )
    amount_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    base_category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4), nullable=True)
    formula_expr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_month: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_month: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    updated_by_id: Mapped[Optional[int]] = mapped_column(
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

    def __repr__(self) -> str:
        return (
            f"<ForecastLine(id={self.id}, scenario_id={self.scenario_id}, "
            f"category_id={self.category_id}, method={self.method.value})>"
        )
