"""Endpoints /api/rules — CRUD + preview + apply + reorder."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal, Optional

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import func as sqlfunc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import (
    accessible_entity_ids_subquery,
    get_current_user,
    require_entity_access,
)
from app.models.bank_account import BankAccount
from app.models.categorization_rule import CategorizationRule
from app.models.transaction import Transaction
from app.models.user import User, UserRole
from app.schemas.categorization_rule import (
    RuleApplyResponse,
    RuleCreate,
    RulePreviewRequest,
    RulePreviewResponse,
    RuleRead,
    RuleReorderItem,
    RuleSampleTransaction,
    RuleSuggestion,
    RuleUpdate,
)
from app.services.audit import record_audit, to_dict_for_audit
from app.services.audit_batch import record_batch_audit
from app.services.categorization import apply_rule as apply_rule_service
from app.services.categorization import preview_rule as preview_rule_service

router = APIRouter(prefix="/api/rules", tags=["rules"])


def _accessible_entity_ids(session: Session, user: User) -> list[int]:
    return list(
        session.scalars(accessible_entity_ids_subquery(session=session, user=user))
    )


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
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[RuleRead]:
    # Sous-requête : nombre de transactions catégorisées par chaque règle.
    hit_count_sq = (
        select(
            Transaction.categorization_rule_id,
            sqlfunc.count(Transaction.id).label("cnt"),
        )
        .where(Transaction.categorization_rule_id.isnot(None))
        .group_by(Transaction.categorization_rule_id)
        .subquery()
    )

    q = select(
        CategorizationRule,
        sqlfunc.coalesce(hit_count_sq.c.cnt, 0).label("hit_count"),
    ).outerjoin(
        hit_count_sq,
        hit_count_sq.c.categorization_rule_id == CategorizationRule.id,
    )

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
    q = q.limit(limit).offset(offset)
    rows = session.execute(q).all()
    result = []
    for rule, hit_count in rows:
        rd = RuleRead.model_validate(rule)
        rd.hit_count = hit_count
        result.append(rd)
    return result


class AutoSuggestItem(BaseModel):
    normalized_label: str
    category_id: int
    category_name: str
    manual_count: int


@router.get("/auto-suggest", response_model=list[AutoSuggestItem])
def auto_suggest(
    entity_id: int | None = Query(default=None),
    min_count: int = Query(default=3, ge=2, le=20),
    days: int = Query(default=30, ge=7, le=90),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[AutoSuggestItem]:
    """Retourne les patterns MANUAL répétés qui méritent une règle automatique.

    Interroge la table transactions pour les transactions catégorisées manuellement
    (categorized_by=MANUAL, categorization_rule_id IS NULL) dans les <days> derniers
    jours. Regroupe par (normalized_label, category_id), filtre >= min_count
    occurrences. Exclut les patterns déjà couverts par une règle existante.
    Multi-tenant : seules les entités accessibles de l'utilisateur sont scannées.
    """
    from app.models.category import Category as CategoryModel
    from app.models.transaction import TransactionCategorizationSource

    since = datetime.utcnow() - timedelta(days=days)
    accessible_ids = _accessible_entity_ids(session, user)

    conditions = [
        Transaction.categorized_by == TransactionCategorizationSource.MANUAL,
        Transaction.categorization_rule_id.is_(None),
        Transaction.normalized_label.isnot(None),
        Transaction.normalized_label != "",
        Transaction.updated_at >= since,
        BankAccount.entity_id.in_(accessible_ids),
    ]
    if entity_id is not None:
        require_entity_access(session=session, user=user, entity_id=entity_id)
        conditions.append(BankAccount.entity_id == entity_id)

    rows = session.execute(
        select(
            Transaction.normalized_label.label("norm_label"),
            Transaction.category_id.label("cat_id"),
            sqlfunc.count(Transaction.id).label("cnt"),
        )
        .join(BankAccount, BankAccount.id == Transaction.bank_account_id)
        .where(sa.and_(*conditions))
        .group_by(Transaction.normalized_label, Transaction.category_id)
        .having(sqlfunc.count(Transaction.id) >= min_count)
        .order_by(sqlfunc.count(Transaction.id).desc())
        .limit(10)
    ).all()

    if not rows:
        return []

    # Charger les catégories pour les noms
    cat_ids = {r.cat_id for r in rows if r.cat_id is not None}
    cats = {}
    if cat_ids:
        cats = {
            c.id: c.name
            for c in session.execute(
                select(CategoryModel).where(CategoryModel.id.in_(cat_ids))
            ).scalars().all()
        }

    # Filtrer les labels déjà couverts par une règle existante (CONTAINS/EQUALS)
    existing_label_values = set(
        session.execute(
            select(CategorizationRule.label_value).where(
                CategorizationRule.label_value.isnot(None)
            )
        ).scalars().all()
    )

    result = []
    for r in rows:
        if r.cat_id is None:
            continue
        # Exclure si déjà couvert par une règle (label_value est contenu dans le pattern)
        if any(
            (r.norm_label or "").upper() in (lv or "").upper()
            or (lv or "").upper() in (r.norm_label or "").upper()
            for lv in existing_label_values
        ):
            continue
        result.append(AutoSuggestItem(
            normalized_label=r.norm_label,
            category_id=r.cat_id,
            category_name=cats.get(r.cat_id, f"#{r.cat_id}"),
            manual_count=r.cnt,
        ))

    return result


@router.post("", response_model=RuleRead, status_code=status.HTTP_201_CREATED)
def create_rule(
    payload: RuleCreate,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> RuleRead:
    _require_editor(user)
    if payload.entity_id is not None:
        require_entity_access(session=session, user=user, entity_id=payload.entity_id)

    rule = CategorizationRule(
        name=payload.name,
        entity_id=payload.entity_id,
        priority=payload.priority,
        is_system=False,
        label_operator=payload.label_operator,
        label_value=payload.label_value,
        direction=payload.direction,
        amount_operator=payload.amount_operator,
        amount_value=payload.amount_value,
        amount_value2=payload.amount_value2,
        counterparty_id=payload.counterparty_id,
        bank_account_id=payload.bank_account_id,
        category_id=payload.category_id,
        created_by_id=user.id,
    )
    session.add(rule)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "RULE_DUPLICATE_PRIORITY",
                "message": "Priorité déjà utilisée dans ce scope",
            },
        )
    record_audit(
        session, user=user, action="create", entity=rule,
        before=None, after=to_dict_for_audit(rule), request=request,
    )
    session.commit()
    session.refresh(rule)
    return RuleRead.model_validate(rule)


_STRUCTURAL_FIELDS = {
    "label_operator", "label_value", "direction",
    "amount_operator", "amount_value", "amount_value2",
    "counterparty_id", "bank_account_id", "category_id",
}


@router.patch("/{rule_id}", response_model=RuleRead)
def update_rule(
    rule_id: int,
    payload: RuleUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> RuleRead:
    _require_editor(user)
    rule = session.get(CategorizationRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Règle introuvable")
    if rule.entity_id is not None:
        require_entity_access(session=session, user=user, entity_id=rule.entity_id)

    data = payload.model_dump(exclude_unset=True)

    # Si l'utilisateur change le scope, vérifier qu'il a accès à la nouvelle
    # entité cible. None = global (autorisé à tout utilisateur éditeur).
    if "entity_id" in data and data["entity_id"] is not None:
        require_entity_access(
            session=session, user=user, entity_id=data["entity_id"]
        )

    if rule.is_system:
        struct_touched = set(data.keys()) & _STRUCTURAL_FIELDS
        if struct_touched:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "RULE_SYSTEM_MUTATE",
                        "message": "Règle système : seuls le nom, la priorité et le scope (société) sont modifiables"},
            )

    before_snapshot = to_dict_for_audit(rule)
    for field, value in data.items():
        setattr(rule, field, value)

    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "RULE_DUPLICATE_PRIORITY",
                    "message": "Priorité déjà utilisée dans ce scope"},
        )
    record_audit(
        session, user=user, action="update", entity=rule,
        before=before_snapshot, after=to_dict_for_audit(rule), request=request,
    )
    session.commit()
    session.refresh(rule)
    return RuleRead.model_validate(rule)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(
    rule_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> None:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Droits administrateur requis")
    rule = session.get(CategorizationRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Règle introuvable")
    if rule.is_system:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "RULE_SYSTEM_DELETE",
                    "message": "Une règle système ne peut pas être supprimée"},
        )
    if rule.entity_id is not None:
        require_entity_access(session=session, user=user, entity_id=rule.entity_id)
    before_snapshot = to_dict_for_audit(rule)
    record_audit(
        session, user=user, action="delete", entity=rule,
        before=before_snapshot, after=None, request=request,
    )
    session.delete(rule)
    session.commit()


@router.post("/preview", response_model=RulePreviewResponse)
def preview_rule_endpoint(
    payload: RulePreviewRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> RulePreviewResponse:
    if payload.entity_id is not None:
        require_entity_access(session=session, user=user, entity_id=payload.entity_id)

    draft = CategorizationRule(
        name=payload.name,
        entity_id=payload.entity_id,
        priority=payload.priority,
        label_operator=payload.label_operator,
        label_value=payload.label_value,
        direction=payload.direction,
        amount_operator=payload.amount_operator,
        amount_value=payload.amount_value,
        amount_value2=payload.amount_value2,
        counterparty_id=payload.counterparty_id,
        bank_account_id=payload.bank_account_id,
        category_id=payload.category_id,
    )
    accessible_ids = _accessible_entity_ids(session=session, user=user)
    result = preview_rule_service(
        session, draft, sample_limit=20, accessible_entity_ids=accessible_ids,
    )
    return RulePreviewResponse(
        matching_count=result.matching_count,
        sample=[RuleSampleTransaction(**s.__dict__) for s in result.sample],
    )


@router.post("/{rule_id}/apply", response_model=RuleApplyResponse)
def apply_rule_endpoint(
    rule_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> RuleApplyResponse:
    _require_editor(user)
    rule = session.get(CategorizationRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Règle introuvable")
    if rule.entity_id is not None:
        require_entity_access(session=session, user=user, entity_id=rule.entity_id)

    report = apply_rule_service(session, rule)
    # Audit batch : 1 ligne résumant l'application (update N transactions).
    if report.updated_count > 0:
        record_batch_audit(
            session,
            user=user,
            request=request,
            action="update",
            entity_type="Transaction",
            entity_id=f"rule-apply({rule.id})",
            after={
                "operation": "rule_apply",
                "rule_id": rule.id,
                "rule_name": rule.name,
                "updated_count": report.updated_count,
            },
        )
    session.commit()
    return RuleApplyResponse(updated_count=report.updated_count)


@router.post("/reorder", response_model=list[RuleRead])
def reorder_rules(
    items: list[RuleReorderItem],
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[RuleRead]:
    _require_editor(user)
    if not items:
        raise HTTPException(status_code=422, detail="Liste vide")

    ids = [i.id for i in items]
    rules = session.execute(
        select(CategorizationRule).where(CategorizationRule.id.in_(ids))
    ).scalars().all()
    if len(rules) != len(items):
        raise HTTPException(status_code=404, detail="Une règle au moins est introuvable")

    scopes = {r.entity_id for r in rules}
    if len(scopes) > 1:
        raise HTTPException(
            status_code=422,
            detail="Le réordonnancement doit porter sur un seul scope",
        )
    scope_entity = scopes.pop()
    if scope_entity is not None:
        require_entity_access(session=session, user=user, entity_id=scope_entity)

    by_id = {r.id: r for r in rules}
    before_priorities = {r.id: r.priority for r in rules}
    try:
        for item in items:
            by_id[item.id].priority = item.priority
        session.flush()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "RULE_DUPLICATE_PRIORITY",
                    "message": "Conflit de priorités pendant le réordonnancement"},
        )

    # Audit batch : 1 ligne résumant le réordonnancement.
    record_batch_audit(
        session,
        user=user,
        request=request,
        action="update",
        entity_type="CategorizationRule",
        entity_id=f"reorder({len(items)})",
        before={"priorities_before": before_priorities},
        after={
            "operation": "reorder",
            "priorities_after": {i.id: i.priority for i in items},
        },
    )
    session.commit()

    refreshed = session.execute(
        select(CategorizationRule)
        .where(CategorizationRule.id.in_(ids))
        .order_by(CategorizationRule.priority.asc())
    ).scalars().all()
    return [RuleRead.model_validate(r) for r in refreshed]


class FromTxBody(BaseModel):
    transaction_ids: list[int]


@router.post("/from-transactions", response_model=RuleSuggestion)
def suggest_from_transactions(
    body: FromTxBody,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> RuleSuggestion:
    _require_editor(user)
    if not body.transaction_ids:
        raise HTTPException(status_code=422, detail="Sélection vide")

    accessible = _accessible_entity_ids(session, user)
    txs = session.execute(
        select(Transaction)
        .join(BankAccount, Transaction.bank_account_id == BankAccount.id)
        .where(
            Transaction.id.in_(body.transaction_ids),
            BankAccount.entity_id.in_(accessible),
        )
    ).scalars().all()
    if len(txs) != len(body.transaction_ids):
        raise HTTPException(status_code=404, detail="Transactions introuvables")

    labels = [t.normalized_label or "" for t in txs]
    prefix = labels[0]
    for lbl in labels[1:]:
        while prefix and not lbl.startswith(prefix):
            prefix = prefix[:-1]
    fallback = (labels[0].split() or [""])[0]
    suggested_value = prefix.strip() or fallback
    suggested_op: str = "STARTS_WITH" if prefix.strip() else "CONTAINS"

    signs = {t.amount > 0 for t in txs}
    if signs == {True}:
        direction = "CREDIT"
    elif signs == {False}:
        direction = "DEBIT"
    else:
        direction = "ANY"

    accounts = {t.bank_account_id for t in txs}
    suggested_bank = accounts.pop() if len(accounts) == 1 else None

    return RuleSuggestion(
        suggested_label_operator=suggested_op,
        suggested_label_value=suggested_value,
        suggested_direction=direction,
        suggested_bank_account_id=suggested_bank,
        transaction_count=len(txs),
    )
