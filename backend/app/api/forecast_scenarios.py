"""Endpoints /api/forecast/scenarios — CRUD + gestion du flag is_default."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_entity_access
from app.models.forecast_scenario import ForecastScenario
from app.models.user import User
from app.models.user_entity_access import UserEntityAccess
from app.schemas.forecast import ScenarioCreate, ScenarioRead, ScenarioUpdate
from app.services.audit import record_audit, to_dict_for_audit

router = APIRouter(prefix="/api/forecast/scenarios", tags=["forecast-scenarios"])


def _accessible_entity_ids(session: Session, user: User) -> list[int]:
    return list(
        session.scalars(
            select(UserEntityAccess.entity_id).where(
                UserEntityAccess.user_id == user.id
            )
        )
    )


def _get_scenario_or_404(session: Session, scenario_id: int) -> ForecastScenario:
    sc = session.get(ForecastScenario, scenario_id)
    if sc is None:
        raise HTTPException(status_code=404, detail="Scénario introuvable")
    return sc


def _unset_other_defaults(
    session: Session, entity_id: int, *, except_id: int | None = None
) -> None:
    """Positionne `is_default=False` sur tous les autres scénarios de l'entité."""
    stmt = update(ForecastScenario).where(
        ForecastScenario.entity_id == entity_id,
        ForecastScenario.is_default.is_(True),
    )
    if except_id is not None:
        stmt = stmt.where(ForecastScenario.id != except_id)
    stmt = stmt.values(is_default=False)
    session.execute(stmt)


@router.get("", response_model=list[ScenarioRead])
def list_scenarios(
    entity_id: int | None = Query(default=None),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[ScenarioRead]:
    accessible = _accessible_entity_ids(session, user)
    if entity_id is not None:
        if entity_id not in accessible:
            raise HTTPException(status_code=403, detail="Entité non accessible")
        where = [ForecastScenario.entity_id == entity_id]
    else:
        where = [ForecastScenario.entity_id.in_(accessible)]

    rows = list(
        session.scalars(
            select(ForecastScenario)
            .where(*where)
            .order_by(
                ForecastScenario.entity_id,
                ForecastScenario.is_default.desc(),
                ForecastScenario.name,
            )
        )
    )
    return [ScenarioRead.model_validate(r) for r in rows]


@router.post("", response_model=ScenarioRead, status_code=status.HTTP_201_CREATED)
def create_scenario(
    payload: ScenarioCreate,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ScenarioRead:
    require_entity_access(session=session, user=user, entity_id=payload.entity_id)

    if payload.is_default:
        _unset_other_defaults(session, payload.entity_id)

    sc = ForecastScenario(
        entity_id=payload.entity_id,
        name=payload.name,
        description=payload.description,
        is_default=payload.is_default,
        created_by_id=user.id,
    )
    session.add(sc)
    session.flush()
    record_audit(
        session, user=user, action="create", entity=sc,
        before=None, after=to_dict_for_audit(sc), request=request,
    )
    session.commit()
    session.refresh(sc)
    return ScenarioRead.model_validate(sc)


@router.patch("/{scenario_id}", response_model=ScenarioRead)
def update_scenario(
    scenario_id: int,
    payload: ScenarioUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ScenarioRead:
    sc = _get_scenario_or_404(session, scenario_id)
    require_entity_access(session=session, user=user, entity_id=sc.entity_id)

    before_snapshot = to_dict_for_audit(sc)
    updates = payload.model_dump(exclude_unset=True)
    if updates.get("is_default") is True:
        _unset_other_defaults(session, sc.entity_id, except_id=sc.id)

    for field, value in updates.items():
        setattr(sc, field, value)
    session.flush()
    record_audit(
        session, user=user, action="update", entity=sc,
        before=before_snapshot, after=to_dict_for_audit(sc), request=request,
    )
    session.commit()
    session.refresh(sc)
    return ScenarioRead.model_validate(sc)


@router.delete("/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scenario(
    scenario_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> None:
    sc = _get_scenario_or_404(session, scenario_id)
    require_entity_access(session=session, user=user, entity_id=sc.entity_id)

    count = session.scalar(
        select(func.count(ForecastScenario.id)).where(
            ForecastScenario.entity_id == sc.entity_id
        )
    ) or 0
    if count <= 1:
        raise HTTPException(
            status_code=409,
            detail="Impossible de supprimer : l'entité doit conserver au moins un scénario",
        )

    before_snapshot = to_dict_for_audit(sc)
    record_audit(
        session, user=user, action="delete", entity=sc,
        before=before_snapshot, after=None, request=request,
    )
    was_default = sc.is_default
    session.delete(sc)
    session.flush()

    if was_default:
        # Promeut un autre scénario de l'entité comme default.
        other = session.scalars(
            select(ForecastScenario)
            .where(ForecastScenario.entity_id == sc.entity_id)
            .order_by(ForecastScenario.created_at, ForecastScenario.id)
            .limit(1)
        ).first()
        if other is not None:
            other.is_default = True

    session.commit()
