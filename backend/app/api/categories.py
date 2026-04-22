"""Endpoints /api/categories."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models.category import Category
from app.models.user import User
from app.schemas.category import CategoryListItem

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryListItem])
def list_categories(
    entity_id: int | None = Query(None),  # noqa: ARG001 — no-op, compat future
    session: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[Category]:
    """Liste des catégories.

    Les catégories sont globales (pas de rattachement à une entité).
    Le paramètre `entity_id` est accepté mais ignoré pour compatibilité
    future ; la réponse est identique qu'il soit fourni ou non.
    """
    stmt = select(Category).order_by(Category.name)
    return list(session.execute(stmt).scalars().all())
