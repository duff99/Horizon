"""Endpoints `/api/analysis/*` — indicateurs KPI pour la page Analyse."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_entity_access
from app.models.user import User
from app.schemas.analysis import (
    CategoryDriftDetailResponse,
    CategoryDriftResponse,
    ClientConcentrationResponse,
    EntitiesComparisonResponse,
    ForecastVarianceResponse,
    RunwayResponse,
    TopMoversResponse,
    WorkingCapitalResponse,
    YoYResponse,
)
from app.services.analysis import (
    compute_category_drift,
    compute_category_drift_detail,
    compute_client_concentration,
    compute_entities_comparison,
    compute_forecast_variance,
    compute_runway,
    compute_top_movers,
    compute_working_capital,
    compute_yoy,
)

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/category-drift", response_model=CategoryDriftResponse)
def get_category_drift(
    entity_id: int = Query(...),
    seuil_pct: float = Query(20.0, ge=0.0, le=500.0),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> CategoryDriftResponse:
    require_entity_access(session=session, user=user, entity_id=entity_id)
    return compute_category_drift(
        session, entity_id=entity_id, seuil_pct=seuil_pct
    )


@router.get(
    "/category-drift/{category_id}/transactions",
    response_model=CategoryDriftDetailResponse,
)
def get_category_drift_detail(
    category_id: int,
    entity_id: int = Query(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> CategoryDriftDetailResponse:
    """Liste des transactions du mois courant pour une catégorie donnée.

    Drill-down depuis le tableau Dérives par catégorie : permet à
    l'utilisateur de voir précisément quelles transactions expliquent
    une dérive ("+45 % sur Loyer ce mois → 3 prélèvements de 1500 €").
    """
    require_entity_access(session=session, user=user, entity_id=entity_id)
    return compute_category_drift_detail(
        session, entity_id=entity_id, category_id=category_id
    )


@router.get("/top-movers", response_model=TopMoversResponse)
def get_top_movers(
    entity_id: int = Query(...),
    limit: int = Query(5, ge=1, le=50),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> TopMoversResponse:
    require_entity_access(session=session, user=user, entity_id=entity_id)
    return compute_top_movers(session, entity_id=entity_id, limit=limit)


@router.get("/runway", response_model=RunwayResponse)
def get_runway(
    entity_id: int = Query(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> RunwayResponse:
    require_entity_access(session=session, user=user, entity_id=entity_id)
    return compute_runway(session, entity_id=entity_id)


@router.get("/yoy", response_model=YoYResponse)
def get_yoy(
    entity_id: int = Query(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> YoYResponse:
    require_entity_access(session=session, user=user, entity_id=entity_id)
    return compute_yoy(session, entity_id=entity_id)


@router.get("/client-concentration", response_model=ClientConcentrationResponse)
def get_client_concentration(
    entity_id: int = Query(...),
    months: int = Query(12, ge=1, le=60),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ClientConcentrationResponse:
    require_entity_access(session=session, user=user, entity_id=entity_id)
    return compute_client_concentration(
        session, entity_id=entity_id, months=months
    )


@router.get("/entities-comparison", response_model=EntitiesComparisonResponse)
def get_entities_comparison(
    months: int = Query(1, ge=1, le=60),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> EntitiesComparisonResponse:
    return compute_entities_comparison(session, user=user, months=months)


@router.get("/forecast-variance", response_model=ForecastVarianceResponse)
def get_forecast_variance(
    entity_id: int = Query(...),
    months: int = Query(6, ge=1, le=24),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ForecastVarianceResponse:
    """Compare prévisionnel vs réalisé sur N mois (mois courant inclus).

    Permet de répondre à la question "mes prévisions sont-elles fiables ?".
    Si aucune entrée prévisionnelle n'existe, has_forecast=False (l'UI
    affichera un état vide avec un lien vers la page Prévisionnel).
    """
    require_entity_access(session=session, user=user, entity_id=entity_id)
    return compute_forecast_variance(
        session, entity_id=entity_id, months=months
    )


@router.get("/working-capital", response_model=WorkingCapitalResponse)
def get_working_capital(
    entity_id: int = Query(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> WorkingCapitalResponse:
    """KPI de besoin en fonds de roulement (DSO, DPO, BFR).

    Calculé à partir de la table commitments. Si aucun engagement n'existe,
    has_data=False (l'UI affichera un état vide avec un lien vers Engagements).
    """
    require_entity_access(session=session, user=user, entity_id=entity_id)
    return compute_working_capital(session, entity_id=entity_id)
