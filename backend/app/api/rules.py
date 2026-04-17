"""Endpoints /api/rules — CRUD + preview + apply + reorder."""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_entity_access
from app.models.categorization_rule import CategorizationRule
from app.models.user import User, UserRole
from app.models.user_entity_access import UserEntityAccess
from app.schemas.categorization_rule import RuleRead

router = APIRouter(prefix="/api/rules", tags=["rules"])


def _accessible_entity_ids(session: Session, user: User) -> list[int]:
    rows = session.execute(
        select(UserEntityAccess.entity_id).where(
            UserEntityAccess.user_id == user.id
        )
    ).scalars().all()
    return list(rows)


def _require_editor(user: User) -> None:
    if user.role == UserRole.READER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Droits éditeur requis",
        )


@router.get("", response_model=list[RuleRead])
def list_rules(
    scope: Optional[Literal["global", "entity", "all"]] = Query(default="all"),
    entity_id: Optional[int] = Query(default=None),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[RuleRead]:
    q = select(CategorizationRule)

    if entity_id is not None:
        require_entity_access(session=session, user=user, entity_id=entity_id)
        q = q.where(CategorizationRule.entity_id == entity_id)
    elif scope == "global":
        q = q.where(CategorizationRule.entity_id.is_(None))
    elif scope == "entity":
        accessible = _accessible_entity_ids(session, user)
        q = q.where(CategorizationRule.entity_id.in_(accessible))
    else:
        accessible = _accessible_entity_ids(session, user)
        q = q.where(
            (CategorizationRule.entity_id.is_(None))
            | (CategorizationRule.entity_id.in_(accessible))
        )

    q = q.order_by(
        CategorizationRule.entity_id.asc().nulls_last(),
        CategorizationRule.priority.asc(),
    )
    rows = session.execute(q).scalars().all()
    return [RuleRead.model_validate(r) for r in rows]
