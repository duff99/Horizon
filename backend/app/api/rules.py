"""Endpoints /api/rules — CRUD + preview + apply + reorder."""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_entity_access
from app.models.audit_log import AuditLog
from app.models.bank_account import BankAccount
from app.models.categorization_rule import CategorizationRule
from app.models.transaction import Transaction
from app.models.user import User, UserRole
from app.models.user_entity_access import UserEntityAccess
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
from app.services.audit import _extract_request_meta, record_audit, to_dict_for_audit
from app.services.categorization import apply_rule as apply_rule_service
from app.services.categorization import preview_rule as preview_rule_service

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

    if rule.is_system:
        struct_touched = set(data.keys()) & _STRUCTURAL_FIELDS
        if struct_touched:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "RULE_SYSTEM_MUTATE",
                        "message": "Règle système : seuls le nom et la priorité sont modifiables"},
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
    _require_editor(user)
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
    result = preview_rule_service(session, draft, sample_limit=20)
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
        try:
            meta = _extract_request_meta(request)
            session.add(
                AuditLog(
                    user_id=user.id,
                    user_email=user.email,
                    action="update",
                    entity_type="Transaction",
                    entity_id=f"rule-apply({rule.id})",
                    before_json=None,
                    after_json={
                        "operation": "rule_apply",
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "updated_count": report.updated_count,
                    },
                    diff_json=None,
                    ip_address=meta["ip_address"],
                    user_agent=meta["user_agent"],
                    request_id=meta["request_id"],
                )
            )
            session.flush()
        except Exception:
            import logging
            logging.getLogger(__name__).exception("audit.rule_apply_failed")
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
    try:
        meta = _extract_request_meta(request)
        session.add(
            AuditLog(
                user_id=user.id,
                user_email=user.email,
                action="update",
                entity_type="CategorizationRule",
                entity_id=f"reorder({len(items)})",
                before_json={"priorities_before": before_priorities},
                after_json={
                    "operation": "reorder",
                    "priorities_after": {i.id: i.priority for i in items},
                },
                diff_json=None,
                ip_address=meta["ip_address"],
                user_agent=meta["user_agent"],
                request_id=meta["request_id"],
            )
        )
        session.flush()
    except Exception:
        import logging
        logging.getLogger(__name__).exception("audit.rules_reorder_failed")
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
