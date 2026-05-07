"""Endpoints `/api/analysis/*` — indicateurs KPI pour la page Analyse."""
from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api._export_helpers import XLSX_AVAILABLE, export_response
from app.db import get_db
from app.deps import get_current_user, require_entity_access
from app.models.user import User
from app.schemas.analysis import (
    CategoryDriftDetailResponse,
    CategoryDriftResponse,
    ClientConcentrationResponse,
    EntitiesComparisonResponse,
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


# ---------------------------------------------------------------------------
# G11 — Endpoints export CSV
# ---------------------------------------------------------------------------


def _check_xlsx(format: str) -> None:
    """Lève HTTPException 400 si XLSX demandé mais openpyxl absent."""
    if format == "xlsx" and not XLSX_AVAILABLE:
        raise HTTPException(status_code=400, detail="Format XLSX non disponible sur ce serveur.")


@router.get("/drift/export")
def export_drift(
    entity_id: int = Query(...),
    seuil_pct: float = Query(20.0, ge=0.0, le=500.0),
    format: Literal["csv", "xlsx"] = Query(default="csv"),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> StreamingResponse:
    """Export CSV des dérives par catégorie (G11).

    Colonnes : Catégorie, M-1 (EUR), Moyenne M-2/M-4 (EUR), Écart (EUR), Écart %.
    """
    _check_xlsx(format)
    require_entity_access(session=session, user=user, entity_id=entity_id)
    result = compute_category_drift(session, entity_id=entity_id, seuil_pct=seuil_pct)

    headers = ["Categorie", "M-1 (EUR)", "Moyenne M-2/M-4 (EUR)", "Ecart (EUR)", "Ecart %", "Statut"]
    rows = [
        [
            row.label,
            f"{row.current_cents / 100:.2f}",
            f"{row.avg3m_cents / 100:.2f}",
            f"{row.delta_cents / 100:.2f}",
            f"{row.delta_pct:.1f}" if row.delta_pct is not None else "",
            row.status,
        ]
        for row in result.rows
    ]

    today = date.today().isoformat()
    filename_base = f"analyse-drift_{today}"
    try:
        return export_response(headers, rows, filename_base, format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/top-movers/export")
def export_top_movers(
    entity_id: int = Query(...),
    limit: int = Query(5, ge=1, le=50),
    format: Literal["csv", "xlsx"] = Query(default="csv"),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> StreamingResponse:
    """Export CSV des top movers (G11).

    Colonnes : Catégorie, Direction, Variation (EUR).
    """
    _check_xlsx(format)
    require_entity_access(session=session, user=user, entity_id=entity_id)
    result = compute_top_movers(session, entity_id=entity_id, limit=limit)

    headers = ["Categorie", "Direction", "Variation (EUR)"]
    rows = []
    for row in result.increases + result.decreases:
        rows.append([
            row.label,
            "encaissement" if row.direction == "in" else "decaissement",
            f"{row.delta_cents / 100:.2f}",
        ])

    today = date.today().isoformat()
    filename_base = f"analyse-top-movers_{today}"
    try:
        return export_response(headers, rows, filename_base, format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/yoy/export")
def export_yoy(
    entity_id: int = Query(...),
    format: Literal["csv", "xlsx"] = Query(default="csv"),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> StreamingResponse:
    """Export CSV de l'analyse YoY (G11).

    Colonnes : Mois, Encaissements N, Encaissements N-1, Décaissements N, Décaissements N-1.
    """
    _check_xlsx(format)
    require_entity_access(session=session, user=user, entity_id=entity_id)
    result = compute_yoy(session, entity_id=entity_id)

    headers = [
        "Mois",
        "Encaissements N (EUR)",
        "Encaissements N-1 (EUR)",
        "Decaissements N (EUR)",
        "Decaissements N-1 (EUR)",
    ]
    rows = [
        [
            pt.month,
            f"{pt.revenues_current / 100:.2f}",
            f"{pt.revenues_previous / 100:.2f}",
            f"{pt.expenses_current / 100:.2f}",
            f"{pt.expenses_previous / 100:.2f}",
        ]
        for pt in result.series
    ]

    today = date.today().isoformat()
    filename_base = f"analyse-yoy_{today}"
    try:
        return export_response(headers, rows, filename_base, format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
