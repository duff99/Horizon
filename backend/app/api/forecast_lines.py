"""Endpoints /api/forecast/lines — CRUD upsert + validate-formula."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_entity_access
from app.models.forecast_line import ForecastLine, ForecastLineMethod
from app.models.forecast_scenario import ForecastScenario
from app.models.user import User
from app.schemas.forecast import (
    ForecastMethod,
    LineRead,
    LineUpsert,
    ValidateFormulaRequest,
    ValidateFormulaResponse,
)
from app.services.audit import record_audit, to_dict_for_audit
from app.services.formula_parser import FormulaError, detect_cycle, parse as formula_parse

router = APIRouter(prefix="/api/forecast/lines", tags=["forecast-lines"])


def _get_scenario_with_access(
    session: Session, user: User, scenario_id: int,
) -> ForecastScenario:
    sc = session.get(ForecastScenario, scenario_id)
    if sc is None:
        raise HTTPException(status_code=404, detail="Scénario introuvable")
    require_entity_access(session=session, user=user, entity_id=sc.entity_id)
    return sc


@router.get("", response_model=list[LineRead])
def list_lines(
    scenario_id: int = Query(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[LineRead]:
    _get_scenario_with_access(session, user, scenario_id)
    rows = list(
        session.scalars(
            select(ForecastLine)
            .where(ForecastLine.scenario_id == scenario_id)
            .order_by(ForecastLine.category_id)
        )
    )
    return [LineRead.model_validate(r) for r in rows]


@router.put("", response_model=LineRead)
def upsert_line(
    payload: LineUpsert,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> LineRead:
    sc = _get_scenario_with_access(session, user, payload.scenario_id)

    if payload.method == ForecastMethod.FORMULA:
        if not (payload.formula_expr and payload.formula_expr.strip()):
            raise HTTPException(
                status_code=422, detail="formula_expr requis et non vide"
            )
        try:
            formula_parse(payload.formula_expr)
        except FormulaError as exc:
            raise HTTPException(
                status_code=422, detail=f"Formule invalide : {exc}"
            ) from exc
        if detect_cycle(
            scenario_id=payload.scenario_id,
            target_category_id=payload.category_id,
            formula_expr=payload.formula_expr,
            session=session,
        ):
            raise HTTPException(
                status_code=422,
                detail="Cycle détecté : la formule référence sa propre catégorie",
            )

    existing = session.scalar(
        select(ForecastLine).where(
            ForecastLine.scenario_id == payload.scenario_id,
            ForecastLine.category_id == payload.category_id,
        )
    )

    method_model = ForecastLineMethod(payload.method.value)

    if existing is None:
        line = ForecastLine(
            scenario_id=payload.scenario_id,
            entity_id=sc.entity_id,
            category_id=payload.category_id,
            method=method_model,
            amount_cents=payload.amount_cents,
            base_category_id=payload.base_category_id,
            ratio=payload.ratio,
            formula_expr=payload.formula_expr,
            start_month=payload.start_month,
            end_month=payload.end_month,
            updated_by_id=user.id,
        )
        session.add(line)
        audit_action: str = "create"
        before_snapshot: dict | None = None
    else:
        line = existing
        audit_action = "update"
        before_snapshot = to_dict_for_audit(line)
        line.method = method_model
        line.amount_cents = payload.amount_cents
        line.base_category_id = payload.base_category_id
        line.ratio = payload.ratio
        line.formula_expr = payload.formula_expr
        line.start_month = payload.start_month
        line.end_month = payload.end_month
        line.updated_by_id = user.id

    session.flush()
    record_audit(
        session, user=user, action=audit_action, entity=line,  # type: ignore[arg-type]
        before=before_snapshot, after=to_dict_for_audit(line), request=request,
    )
    session.commit()
    session.refresh(line)
    return LineRead.model_validate(line)


@router.delete("/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_line(
    line_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> None:
    line = session.get(ForecastLine, line_id)
    if line is None:
        raise HTTPException(status_code=404, detail="Ligne prévisionnelle introuvable")
    require_entity_access(session=session, user=user, entity_id=line.entity_id)
    before_snapshot = to_dict_for_audit(line)
    record_audit(
        session, user=user, action="delete", entity=line,
        before=before_snapshot, after=None, request=request,
    )
    session.delete(line)
    session.commit()


@router.post("/validate-formula", response_model=ValidateFormulaResponse)
def validate_formula(
    payload: ValidateFormulaRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ValidateFormulaResponse:
    """Valide une expression de formule.

    Retourne `{valid: true}` si la formule parse sans erreur ET ne contient
    pas de cycle (si `category_id` fourni). Sinon `{valid: false, error: ...}`.
    """
    _get_scenario_with_access(session, user, payload.scenario_id)
    if not payload.formula_expr or not payload.formula_expr.strip():
        return ValidateFormulaResponse(valid=False, error="formula_expr vide")
    try:
        formula_parse(payload.formula_expr)
    except FormulaError as exc:
        return ValidateFormulaResponse(valid=False, error=str(exc))
    if payload.category_id is not None and detect_cycle(
        scenario_id=payload.scenario_id,
        target_category_id=payload.category_id,
        formula_expr=payload.formula_expr,
        session=session,
    ):
        return ValidateFormulaResponse(
            valid=False,
            error="Cycle détecté : la formule référence sa propre catégorie",
        )
    return ValidateFormulaResponse(valid=True, error=None)
