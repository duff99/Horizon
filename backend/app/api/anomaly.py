"""Endpoint GET /api/analysis/anomalies — détection des anomalies p95 (G4)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_entity_access
from app.models.user import User
from app.schemas.anomaly import AnomalyResponse
from app.services.anomaly import detect_anomalies

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/anomalies", response_model=AnomalyResponse)
def get_anomalies(
    entity_id: int = Query(...),
    days: int = Query(180, ge=30, le=730),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnomalyResponse:
    """Retourne les transactions des 30 derniers jours dépassant le p95 historique de leur catégorie."""
    require_entity_access(session=db, user=user, entity_id=entity_id)
    return detect_anomalies(db, entity_id=entity_id, days=days)
