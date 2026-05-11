"""Endpoint /api/transactions."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api._export_helpers import XLSX_AVAILABLE, export_response
from app.db import get_db
from app.deps import (
    accessible_entity_ids_subquery,
    get_current_user,
    require_entity_access,
)
from app.models.bank_account import BankAccount
from app.models.category import Category
from app.models.entity import Entity
from app.models.transaction import Transaction, TransactionCategorizationSource
from app.models.user import User, UserRole
from app.schemas.categorization_rule import BulkCategorizeRequest, BulkCategorizeFilteredRequest
from app.schemas.transaction import (
    TransactionFilter,
    TransactionListResponse,
    TransactionRead,
)
from app.services.audit_batch import record_batch_audit

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("", response_model=TransactionListResponse)
def list_transactions(
    filters: TransactionFilter = Depends(),
    entity_id: int | None = Query(None),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> TransactionListResponse:
    accessible_entity_ids = accessible_entity_ids_subquery(session=session, user=user)

    conditions = [
        BankAccount.entity_id.in_(accessible_entity_ids),
        Transaction.is_aggregation_parent.is_(False),
    ]
    if entity_id is not None:
        # 403 si l'utilisateur n'a pas accès à l'entité demandée
        require_entity_access(session=session, user=user, entity_id=entity_id)
        conditions.append(BankAccount.entity_id == entity_id)
    if filters.bank_account_id:
        conditions.append(Transaction.bank_account_id == filters.bank_account_id)
    if filters.date_from:
        conditions.append(Transaction.operation_date >= filters.date_from)
    if filters.date_to:
        conditions.append(Transaction.operation_date <= filters.date_to)
    if filters.counterparty_id:
        conditions.append(Transaction.counterparty_id == filters.counterparty_id)
    if filters.category_id is not None:
        conditions.append(Transaction.category_id == filters.category_id)
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
    # E7 — masquer les enfants SEPA par défaut (parent_transaction_id IS NULL)
    # Exception : si l'appelant filtre explicitement par counterparty_id, on
    # inclut les enfants SEPA. Les batch parents SEPA n'ont pas de tier, donc
    # demander "tx de ce tiers" sans les enfants renverrait souvent 0 ligne
    # (cas des salaires/fournisseurs payés par lot SEPA).
    if not filters.include_sepa_children and not filters.counterparty_id:
        conditions.append(Transaction.parent_transaction_id.is_(None))
    # E8 — filtres montant (valeur absolue, cohérent avec RuleForm)
    if filters.amount_min is not None:
        conditions.append(func.abs(Transaction.amount) >= filters.amount_min)
    if filters.amount_max is not None:
        conditions.append(func.abs(Transaction.amount) <= filters.amount_max)

    base_q = (
        select(Transaction, Entity.id.label("entity_id"), Entity.name.label("entity_name"))
        .join(BankAccount, BankAccount.id == Transaction.bank_account_id)
        .join(Entity, Entity.id == BankAccount.entity_id)
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
    ).all()

    items = []
    for tx, ent_id, ent_name in rows:
        data = {
            "id": tx.id,
            "operation_date": tx.operation_date,
            "value_date": tx.value_date,
            "label": tx.label,
            "raw_label": tx.raw_label,
            "amount": tx.amount,
            "is_aggregation_parent": tx.is_aggregation_parent,
            "parent_transaction_id": tx.parent_transaction_id,
            "counterparty": tx.counterparty,
            "category": tx.category,
            "entity_id": ent_id,
            "entity_name": ent_name,
        }
        items.append(TransactionRead.model_validate(data))

    return TransactionListResponse(
        items=items,
        total=total,
        page=filters.page,
        per_page=filters.per_page,
    )


@router.get("/export")
def export_transactions(
    entity_id: int | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    bank_account_id: int | None = Query(None),
    category_id: int | None = Query(None),
    counterparty_id: int | None = Query(None),
    search: str | None = Query(None),
    uncategorized: bool | None = Query(None),
    amount_min: Decimal | None = Query(None),
    amount_max: Decimal | None = Query(None),
    include_sepa_children: bool = Query(False),
    format: Literal["csv", "xlsx"] = Query(default="csv"),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> StreamingResponse:
    """Export CSV (ou XLSX si disponible) des transactions filtrées.

    Réutilise les mêmes filtres que GET /api/transactions.
    Colonnes : Date, Libellé, Tiers, Catégorie, Montant (€), Compte.
    Multi-tenant : seules les transactions des entités accessibles sont exportées.
    """
    if format == "xlsx" and not XLSX_AVAILABLE:
        raise HTTPException(status_code=400, detail="Format XLSX non disponible sur ce serveur.")

    accessible_entity_ids = accessible_entity_ids_subquery(session=session, user=user)

    conditions = [
        BankAccount.entity_id.in_(accessible_entity_ids),
        Transaction.is_aggregation_parent.is_(False),
    ]
    if entity_id is not None:
        require_entity_access(session=session, user=user, entity_id=entity_id)
        conditions.append(BankAccount.entity_id == entity_id)
    if bank_account_id:
        conditions.append(Transaction.bank_account_id == bank_account_id)
    if date_from:
        conditions.append(Transaction.operation_date >= date_from)
    if date_to:
        conditions.append(Transaction.operation_date <= date_to)
    if counterparty_id:
        conditions.append(Transaction.counterparty_id == counterparty_id)
    if category_id is not None:
        conditions.append(Transaction.category_id == category_id)
    if search:
        like = f"%{search.lower()}%"
        conditions.append(
            or_(
                func.lower(Transaction.label).like(like),
                func.lower(Transaction.raw_label).like(like),
            )
        )
    if uncategorized:
        conditions.append(
            Transaction.categorized_by == TransactionCategorizationSource.NONE
        )
    if not include_sepa_children:
        conditions.append(Transaction.parent_transaction_id.is_(None))
    if amount_min is not None:
        conditions.append(func.abs(Transaction.amount) >= amount_min)
    if amount_max is not None:
        conditions.append(func.abs(Transaction.amount) <= amount_max)

    q = (
        select(Transaction, BankAccount.name.label("account_name"))
        .join(BankAccount, BankAccount.id == Transaction.bank_account_id)
        .where(and_(*conditions))
        .order_by(Transaction.operation_date.desc(), Transaction.statement_row_index.desc())
        .options(
            selectinload(Transaction.counterparty),
            selectinload(Transaction.category),
        )
    )
    results = session.execute(q).all()

    headers_csv = ["Date", "Libelle", "Tiers", "Categorie", "Montant (EUR)", "Compte"]
    rows = []
    for tx, acct_name in results:
        rows.append([
            tx.operation_date.isoformat() if tx.operation_date else "",
            tx.label,
            tx.counterparty.name if tx.counterparty else "",
            tx.category.name if tx.category else "",
            # Montant en euros, point décimal, pas de symbole
            f"{float(tx.amount):.2f}",
            acct_name or "",
        ])

    today = date.today().isoformat()
    filename_base = f"transactions_{today}"
    try:
        return export_response(headers_csv, rows, filename_base, format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/bulk-categorize")
def bulk_categorize(
    payload: BulkCategorizeRequest,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> dict[str, int]:
    if user.role == UserRole.READER:
        raise HTTPException(status_code=403, detail="Droits éditeur requis")

    cat = session.get(Category, payload.category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")

    accessible_entities = accessible_entity_ids_subquery(session=session, user=user)
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

    # Audit batch : 1 seule ligne, pas N. entity_id = liste des ids.
    if txs:
        record_batch_audit(
            session,
            user=user,
            request=request,
            action="update",
            entity_type="Transaction",
            entity_id=f"bulk({len(txs)})",
            after={
                "operation": "bulk_categorize",
                "transaction_ids": [tx.id for tx in txs],
                "category_id": payload.category_id,
                "count": len(txs),
            },
        )
    session.commit()
    return {"updated_count": len(txs)}


@router.post("/bulk-categorize-filtered")
def bulk_categorize_filtered(
    payload: BulkCategorizeFilteredRequest,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> dict[str, int]:
    """Catégorise toutes les transactions correspondant aux filtres sans limite de pagination.

    E6 — Multi-tenant : seules les transactions appartenant aux entités
    accessibles de l'utilisateur courant sont modifiées.
    """
    if user.role == UserRole.READER:
        raise HTTPException(status_code=403, detail="Droits éditeur requis")

    cat = session.get(Category, payload.category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")

    accessible_entity_ids = accessible_entity_ids_subquery(session=session, user=user)

    conditions = [
        BankAccount.entity_id.in_(accessible_entity_ids),
        Transaction.is_aggregation_parent.is_(False),
    ]

    # E7 — masquer les enfants SEPA par défaut
    if not payload.include_sepa_children:
        conditions.append(Transaction.parent_transaction_id.is_(None))

    if payload.entity_id is not None:
        require_entity_access(session=session, user=user, entity_id=payload.entity_id)
        conditions.append(BankAccount.entity_id == payload.entity_id)
    if payload.bank_account_id:
        conditions.append(Transaction.bank_account_id == payload.bank_account_id)
    if payload.date_from:
        conditions.append(Transaction.operation_date >= payload.date_from)
    if payload.date_to:
        conditions.append(Transaction.operation_date <= payload.date_to)
    if payload.counterparty_id:
        conditions.append(Transaction.counterparty_id == payload.counterparty_id)
    if payload.search:
        like = f"%{payload.search.lower()}%"
        conditions.append(
            or_(
                func.lower(Transaction.label).like(like),
                func.lower(Transaction.raw_label).like(like),
            )
        )
    if payload.uncategorized:
        conditions.append(
            Transaction.categorized_by == TransactionCategorizationSource.NONE
        )
    # E8 — filtres montant (valeur absolue)
    if payload.amount_min is not None:
        conditions.append(func.abs(Transaction.amount) >= payload.amount_min)
    if payload.amount_max is not None:
        conditions.append(func.abs(Transaction.amount) <= payload.amount_max)

    txs = session.execute(
        select(Transaction)
        .join(BankAccount, BankAccount.id == Transaction.bank_account_id)
        .where(and_(*conditions))
    ).scalars().all()

    for tx in txs:
        tx.category_id = payload.category_id
        tx.categorized_by = TransactionCategorizationSource.MANUAL

    if txs:
        record_batch_audit(
            session,
            user=user,
            request=request,
            action="update",
            entity_type="Transaction",
            entity_id=f"bulk-filtered({len(txs)})",
            after={
                "operation": "bulk_categorize_filtered",
                "filters": payload.model_dump(exclude={"category_id"}, mode="json"),
                "category_id": payload.category_id,
                "count": len(txs),
            },
        )
    session.commit()
    return {"updated_count": len(txs)}
