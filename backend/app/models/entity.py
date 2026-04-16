from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.models.base import Base


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    siret: Mapped[str | None] = mapped_column(String(32))
    parent_entity_id: Mapped[int | None] = mapped_column(
        ForeignKey("entities.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


def validate_entity_tree(entity: Entity, *, session: Session | None = None) -> None:
    """Validation applicative : pas de self-reference ni de cycle.

    Vérifications :
    1. L'entité ne peut pas être son propre parent.
    2. Aucun cycle dans la chaîne des parents (A→B→A ou plus long).
       (Réalisé au niveau applicatif car Postgres ne l'empêche pas.)
    """
    if entity.id is not None and entity.parent_entity_id == entity.id:
        raise ValueError("Une société ne peut pas être son propre parent")
    # Si une session est fournie et que l'entité a un parent, remonter la chaîne
    if session is None or entity.parent_entity_id is None or entity.id is None:
        return
    seen: set[int] = {entity.id}
    cursor_id: int | None = entity.parent_entity_id
    while cursor_id is not None:
        if cursor_id in seen:
            raise ValueError(
                "Cycle détecté dans la hiérarchie des sociétés "
                f"(via l'identifiant {cursor_id})"
            )
        seen.add(cursor_id)
        parent = session.get(Entity, cursor_id)
        if parent is None:
            raise ValueError(f"Société parente introuvable (id={cursor_id})")
        cursor_id = parent.parent_entity_id
