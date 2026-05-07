"""Modèle SQLAlchemy pour la table drift_acks (G12 — snooze de dérive)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DriftAck(Base):
    """Acquittement/snooze d'une alerte de dérive pour une entité × catégorie."""

    __tablename__ = "drift_acks"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    snoozed_until: Mapped[date] = mapped_column(Date(), nullable=False)
    acknowledged_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    acknowledged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
