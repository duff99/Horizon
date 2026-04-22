from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_admin
from app.models.bank_account import BankAccount
from app.models.entity import Entity, validate_entity_tree
from app.models.user import User
from app.schemas.entity import EntityCreate, EntityRead, EntityUpdate
from app.services.forecast_scenarios import ensure_default_scenario

router = APIRouter(
    prefix="/api/entities", tags=["entities"], dependencies=[Depends(require_admin)]
)


@router.get("", response_model=list[EntityRead])
def list_entities(db: Session = Depends(get_db)) -> list[Entity]:
    return list(db.scalars(select(Entity).order_by(Entity.name)))


@router.post("", response_model=EntityRead, status_code=status.HTTP_201_CREATED)
def create_entity(
    payload: EntityCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Entity:
    e = Entity(**payload.model_dump())
    db.add(e)
    db.flush()
    try:
        validate_entity_tree(e, session=db)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    # Seed : chaque entité doit disposer d'un scénario prévisionnel par défaut.
    ensure_default_scenario(db, e, created_by=current)
    db.commit()
    db.refresh(e)
    return e


@router.patch("/{entity_id}", response_model=EntityRead)
def update_entity(
    entity_id: int, payload: EntityUpdate, db: Session = Depends(get_db)
) -> Entity:
    e = db.get(Entity, entity_id)
    if e is None:
        raise HTTPException(status_code=404, detail="Société introuvable")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(e, field, value)
    try:
        validate_entity_tree(e, session=db)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(e)
    return e


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entity(entity_id: int, db: Session = Depends(get_db)) -> None:
    e = db.get(Entity, entity_id)
    if e is None:
        raise HTTPException(status_code=404, detail="Société introuvable")
    has_accounts = db.scalar(
        select(BankAccount.id).where(BankAccount.entity_id == entity_id)
    )
    if has_accounts:
        raise HTTPException(
            status_code=409,
            detail="Impossible de supprimer : des comptes bancaires sont rattachés",
        )
    has_children = db.scalar(
        select(Entity.id).where(Entity.parent_entity_id == entity_id)
    )
    if has_children:
        raise HTTPException(
            status_code=409,
            detail="Impossible de supprimer : des filiales sont rattachées",
        )
    db.delete(e)
    db.commit()
