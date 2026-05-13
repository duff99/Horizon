"""Snapshot mensuel d'une cellule prévisionnelle, figée pour comparaison."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ForecastMonthSnapshot(Base):
    """Valeur prédite figée pour (scenario, category, month).

    Permet de comparer "ce qui était prévu au moment où le mois est passé"
    contre "ce qui a été réellement importé" — base d'une vue Suivi des
    écarts stable et reproductible (sinon AVG_3M & co donneraient des
    valeurs différentes à chaque consultation, l'historique évoluant).
    """
    __tablename__ = "forecast_month_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "scenario_id",
            "category_id",
            "month",
            name="uq_forecast_snapshot_scenario_category_month",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    scenario_id: Mapped[int] = mapped_column(
        ForeignKey("forecast_scenarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    month: Mapped[date] = mapped_column(Date, nullable=False)
    forecast_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    is_auto: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
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
            f"<ForecastMonthSnapshot(scenario={self.scenario_id}, "
            f"cat={self.category_id}, month={self.month}, "
            f"cents={self.forecast_cents}, auto={self.is_auto})>"
        )
