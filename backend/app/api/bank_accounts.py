from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_admin
from app.models.bank_account import BankAccount
from app.models.entity import Entity
from app.models.user import User
from app.schemas.bank_account import (
    BankAccountCreate,
    BankAccountRead,
    BankAccountUpdate,
)
from app.services.audit import record_audit, to_dict_for_audit

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
    payload: BankAccountCreate,
    request: Request,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin),
) -> BankAccount:
    entity = db.get(Entity, payload.entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Société introuvable")
    ba = BankAccount(**payload.model_dump())
    db.add(ba)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Cet IBAN est déjà enregistré"
        ) from exc
    record_audit(
        db, user=current, action="create", entity=ba,
        before=None, after=to_dict_for_audit(ba), request=request,
    )
    db.commit()
    db.refresh(ba)
    return ba


@router.patch("/{account_id}", response_model=BankAccountRead)
def update_bank_account(
    account_id: int,
    payload: BankAccountUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin),
) -> BankAccount:
    ba = db.get(BankAccount, account_id)
    if ba is None:
        raise HTTPException(status_code=404, detail="Compte bancaire introuvable")
    before_snapshot = to_dict_for_audit(ba)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ba, field, value)
    db.flush()
    record_audit(
        db, user=current, action="update", entity=ba,
        before=before_snapshot, after=to_dict_for_audit(ba), request=request,
    )
    db.commit()
    db.refresh(ba)
    return ba
