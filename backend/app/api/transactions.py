"""Endpoint /api/transactions."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import get_current_user
from app.models.bank_account import BankAccount
from app.models.category import Category
from app.models.transaction import Transaction, TransactionCategorizationSource
from app.models.user import User, UserRole
from app.models.user_entity_access import UserEntityAccess
from app.schemas.categorization_rule import BulkCategorizeRequest
from app.schemas.transaction import (
    TransactionFilter,
    TransactionListResponse,
    TransactionRead,
)

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("", response_model=TransactionListResponse)
def list_transactions(
    filters: TransactionFilter = Depends(),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> TransactionListResponse:
    accessible_entity_ids = select(UserEntityAccess.entity_id).where(
        UserEntityAccess.user_id == user.id
    )

    conditions = [
        BankAccount.entity_id.in_(accessible_entity_ids),
        Transaction.is_aggregation_parent.is_(False),
    ]
    if filters.bank_account_id:
        conditions.append(Transaction.bank_account_id == filters.bank_account_id)
    if filters.date_from:
        conditions.append(Transaction.operation_date >= filters.date_from)
    if filters.date_to:
        conditions.append(Transaction.operation_date <= filters.date_to)
    if filters.counterparty_id:
        conditions.append(Transaction.counterparty_id == filters.counterparty_id)
    if filters.search:
        like = f"%{filters.search.lower()}%"
        conditions.append(
            or_(
                func.lower(Transaction.label).like(like),
                func.lower(Transaction.raw_label).like(like),
            )
        )
    if filters.uncategorized:
        conditions.append(
            Transaction.categorized_by == TransactionCategorizationSource.NONE
        )

    base_q = (
        select(Transaction)
        .join(BankAccount, BankAccount.id == Transaction.bank_account_id)
        .where(and_(*conditions))
        .order_by(
            Transaction.operation_date.desc(),
            Transaction.statement_row_index.desc(),
        )
        .options(
            selectinload(Transaction.counterparty),
            selectinload(Transaction.category),
        )
    )

    total = session.execute(
        select(func.count()).select_from(base_q.subquery())
    ).scalar_one()

    offset = (filters.page - 1) * filters.per_page
    rows = session.execute(
        base_q.offset(offset).limit(filters.per_page)
    ).scalars().all()

    return TransactionListResponse(
        items=[TransactionRead.model_validate(r) for r in rows],
        total=total,
        page=filters.page,
        per_page=filters.per_page,
    )


@router.post("/bulk-categorize")
def bulk_categorize(
    payload: BulkCategorizeRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> dict[str, int]:
    if user.role == UserRole.READER:
        raise HTTPException(status_code=403, detail="Droits éditeur requis")

    cat = session.get(Category, payload.category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")

    accessible_entities = select(UserEntityAccess.entity_id).where(
        UserEntityAccess.user_id == user.id
    )
    accessible_accounts = select(BankAccount.id).where(
        BankAccount.entity_id.in_(accessible_entities)
    )
    txs = session.execute(
        select(Transaction).where(
            Transaction.id.in_(payload.transaction_ids),
            Transaction.bank_account_id.in_(accessible_accounts),
        )
    ).scalars().all()

    for tx in txs:
        tx.category_id = payload.category_id
        tx.categorized_by = TransactionCategorizationSource.MANUAL
    session.commit()
    return {"updated_count": len(txs)}
