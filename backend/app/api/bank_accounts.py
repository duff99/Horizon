from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_admin
from app.models.bank_account import BankAccount
from app.models.entity import Entity
from app.schemas.bank_account import (
    BankAccountCreate,
    BankAccountRead,
    BankAccountUpdate,
)

router = APIRouter(
    prefix="/api/bank-accounts",
    tags=["bank-accounts"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=list[BankAccountRead])
def list_bank_accounts(db: Session = Depends(get_db)) -> list[BankAccount]:
    return list(db.scalars(select(BankAccount).order_by(BankAccount.created_at.desc())))


@router.post("", response_model=BankAccountRead, status_code=status.HTTP_201_CREATED)
def create_bank_account(
    payload: BankAccountCreate, db: Session = Depends(get_db)
) -> BankAccount:
    entity = db.get(Entity, payload.entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Société introuvable")
    ba = BankAccount(**payload.model_dump())
    db.add(ba)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Cet IBAN est déjà enregistré"
        ) from exc
    db.refresh(ba)
    return ba


@router.patch("/{account_id}", response_model=BankAccountRead)
def update_bank_account(
    account_id: int, payload: BankAccountUpdate, db: Session = Depends(get_db)
) -> BankAccount:
    ba = db.get(BankAccount, account_id)
    if ba is None:
        raise HTTPException(status_code=404, detail="Compte bancaire introuvable")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ba, field, value)
    db.commit()
    db.refresh(ba)
    return ba
