"""Endpoints /api/forecast/comparison + /api/forecast/snapshots (clôture mensuelle)."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_entity_access
from app.models.forecast_scenario import ForecastScenario
from app.models.user import User
from app.services.forecast_comparison import (
    ComparisonResult,
    compute_comparison,
    snapshot_month,
)


router = APIRouter(prefix="/api/forecast", tags=["forecast-comparison"])

_MAX_RANGE_MONTHS = 36


def _parse_year_month(value: str, field: str) -> date:
    try:
        y, m = value.split("-")
        return date(int(y), int(m), 1)
    except (ValueError, AttributeError) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Paramètre '{field}' invalide : attendu YYYY-MM (reçu {value!r})",
        ) from exc


def _months_between(a: date, b: date) -> int:
    return (b.year - a.year) * 12 + (b.month - a.month) + 1


def _require_scenario(session: Session, scenario_id: int, entity_id: int) -> ForecastScenario:
    sc = session.get(ForecastScenario, scenario_id)
    if sc is None:
        raise HTTPException(status_code=404, detail="Scénario introuvable")
    if sc.entity_id != entity_id:
        raise HTTPException(
            status_code=403, detail="Scénario non rattaché à cette entité"
        )
    return sc


# ---------------------------------------------------------------------------
# Schemas de réponse
# ---------------------------------------------------------------------------


class ComparisonRowRead(BaseModel):
    category_id: int
    label: str
    direction: str
    forecast_cents: int
    realized_cents: int
    ecart_cents: int
    ecart_pct: float | None = None
    status: str


class ComparisonMonthRead(BaseModel):
    month: str
    is_snapshotted: bool
    rows: list[ComparisonRowRead]
    total_in_forecast_cents: int
    total_in_realized_cents: int
    total_out_forecast_cents: int
    total_out_realized_cents: int
    net_forecast_cents: int
    net_realized_cents: int


class ComparisonResponse(BaseModel):
    months: list[ComparisonMonthRead]


class SnapshotRequest(BaseModel):
    scenario_id: int
    entity_id: int
    month: str  # "YYYY-MM"


class SnapshotResponse(BaseModel):
    snapshotted_count: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/comparison", response_model=ComparisonResponse)
def get_comparison(
    scenario_id: int = Query(...),
    entity_id: int = Query(...),
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ComparisonResponse:
    require_entity_access(session=session, user=user, entity_id=entity_id)
    _require_scenario(session, scenario_id, entity_id)

    from_month = _parse_year_month(from_, "from")
    to_month = _parse_year_month(to, "to")
    if from_month > to_month:
        raise HTTPException(status_code=400, detail="from doit être <= to")
    if _months_between(from_month, to_month) > _MAX_RANGE_MONTHS:
        raise HTTPException(
            status_code=400, detail=f"Plage trop large (max {_MAX_RANGE_MONTHS} mois)"
        )

    result: ComparisonResult = compute_comparison(
        session,
        scenario_id=scenario_id,
        entity_id=entity_id,
        from_month=from_month,
        to_month=to_month,
    )
    return ComparisonResponse(
        months=[
            ComparisonMonthRead(
                month=m.month,
                is_snapshotted=m.is_snapshotted,
                rows=[
                    ComparisonRowRead(
                        category_id=r.category_id,
                        label=r.label,
                        direction=r.direction,
                        forecast_cents=r.forecast_cents,
                        realized_cents=r.realized_cents,
                        ecart_cents=r.ecart_cents,
                        ecart_pct=r.ecart_pct,
                        status=r.status,
                    )
                    for r in m.rows
                ],
                total_in_forecast_cents=m.total_in_forecast_cents,
                total_in_realized_cents=m.total_in_realized_cents,
                total_out_forecast_cents=m.total_out_forecast_cents,
                total_out_realized_cents=m.total_out_realized_cents,
                net_forecast_cents=m.net_forecast_cents,
                net_realized_cents=m.net_realized_cents,
            )
            for m in result.months
        ]
    )


@router.post("/snapshots", response_model=SnapshotResponse)
def post_snapshot(
    payload: SnapshotRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> SnapshotResponse:
    """Re-clôture manuelle d'un mois (replace le snapshot existant)."""
    require_entity_access(session=session, user=user, entity_id=payload.entity_id)
    _require_scenario(session, payload.scenario_id, payload.entity_id)

    month = _parse_year_month(payload.month, "month")
    count = snapshot_month(
        session,
        scenario_id=payload.scenario_id,
        month=month,
        is_auto=False,
    )
    return SnapshotResponse(snapshotted_count=count)
