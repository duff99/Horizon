"""Endpoint /api/forecast/pivot — agrégation pivot (catégorie × mois) pour le prévisionnel v2."""
from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api._export_helpers import XLSX_AVAILABLE, export_response
from app.db import get_db
from app.deps import get_current_user, require_entity_access
from app.models.bank_account import BankAccount
from app.models.forecast_scenario import ForecastScenario
from app.models.user import User
from app.schemas.forecast import (
    PivotCellRead,
    PivotResponse,
    PivotRowRead,
    SeriesPointRead,
)
from app.services.forecast_engine import compute_pivot

router = APIRouter(prefix="/api/forecast", tags=["forecast-pivot"])


_MAX_RANGE_MONTHS = 36


def _parse_year_month(value: str, field: str) -> date:
    """Parse `YYYY-MM` en `date(Y, M, 1)`. Lève HTTPException(400) sinon."""
    try:
        year_str, month_str = value.split("-")
        year = int(year_str)
        month = int(month_str)
        if len(year_str) != 4 or not (1 <= month <= 12):
            raise ValueError
        return date(year, month, 1)
    except (ValueError, AttributeError) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Paramètre '{field}' invalide : attendu format YYYY-MM (reçu {value!r})",
        ) from exc


def _months_between(a: date, b: date) -> int:
    """Nombre de mois entre a et b inclus (a <= b)."""
    return (b.year - a.year) * 12 + (b.month - a.month) + 1


def _parse_accounts_csv(raw: str | None) -> list[int] | None:
    if raw is None or raw.strip() == "":
        return None
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    try:
        return [int(p) for p in parts]
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Paramètre 'accounts' invalide : liste CSV d'entiers attendue",
        ) from exc


@router.get("/pivot", response_model=PivotResponse)
def get_pivot(
    response: Response,
    scenario_id: int = Query(...),
    entity_id: int = Query(...),
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    accounts: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> PivotResponse:
    # 1. Access control entité
    require_entity_access(session=session, user=user, entity_id=entity_id)

    # 2. Scenario appartient à l'entité
    sc = session.get(ForecastScenario, scenario_id)
    if sc is None:
        raise HTTPException(status_code=404, detail="Scénario introuvable")
    if sc.entity_id != entity_id:
        raise HTTPException(
            status_code=403, detail="Scénario non rattaché à cette entité"
        )

    # 3. Validation des dates
    from_month = _parse_year_month(from_, "from")
    to_month = _parse_year_month(to, "to")
    if from_month > to_month:
        raise HTTPException(
            status_code=400, detail="La borne 'from' doit être <= 'to'"
        )
    span = _months_between(from_month, to_month)
    if span > _MAX_RANGE_MONTHS:
        raise HTTPException(
            status_code=400,
            detail=f"Plage trop large : {span} mois (maximum {_MAX_RANGE_MONTHS})",
        )

    # 4. Validation des comptes (doivent appartenir à l'entité)
    account_ids = _parse_accounts_csv(accounts)
    if account_ids is not None:
        entity_account_ids = set(
            session.scalars(
                select(BankAccount.id).where(BankAccount.entity_id == entity_id)
            )
        )
        invalid = [a for a in account_ids if a not in entity_account_ids]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Comptes non rattachés à l'entité : {invalid}",
            )

    # 5. Délègue au moteur
    result = compute_pivot(
        session,
        scenario_id=scenario_id,
        entity_id=entity_id,
        from_month=from_month,
        to_month=to_month,
        account_ids=account_ids,
    )

    # 6. Sérialisation (le moteur renvoie des dataclasses et des dicts "in"/"out",
    #    on normalise vers "in_cents"/"out_cents" côté API).
    rows = [
        PivotRowRead(
            category_id=row.category_id,
            parent_id=row.parent_id,
            label=row.label,
            level=row.level,
            direction=row.direction,
            cells=[
                PivotCellRead(
                    month=result.months[idx],
                    realized_cents=c.realized_cents,
                    committed_cents=c.committed_cents,
                    forecast_cents=c.forecast_cents,
                    total_cents=c.total_cents,
                    line_method=c.line_method,
                    line_params=c.line_params,
                    insufficient_history=c.insufficient_history,
                    sign_anomaly=c.sign_anomaly,
                )
                for idx, c in enumerate(row.cells)
            ],
        )
        for row in result.rows
    ]

    realized_series = [
        SeriesPointRead(
            month=pt["month"], in_cents=pt["in"], out_cents=pt["out"]
        )
        for pt in result.realized_series
    ]
    forecast_series = [
        SeriesPointRead(
            month=pt["month"], in_cents=pt["in"], out_cents=pt["out"]
        )
        for pt in result.forecast_series
    ]

    response.headers["Cache-Control"] = "private, max-age=5"

    return PivotResponse(
        months=result.months,
        opening_balance_cents=result.opening_balance_cents,
        closing_balance_projection_cents=result.closing_balance_projection_cents,
        rows=rows,
        realized_series=realized_series,
        forecast_series=forecast_series,
        uncategorized_net_cents=result.uncategorized_net_cents,
    )


@router.get("/pivot/export")
def export_pivot(
    scenario_id: int = Query(...),
    entity_id: int = Query(...),
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    accounts: str | None = Query(default=None),
    format: Literal["csv", "xlsx"] = Query(default="csv"),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> StreamingResponse:
    """Export CSV (ou XLSX) du tableau pivot prévisionnel (G11).

    Matrice catégorie × mois avec montants réalisés, engagés et prévisionnels.
    Colonnes : Catégorie, Niveau, Direction, puis un triplet (Réalisé, Engagé, Prévisionnel)
    pour chaque mois de la plage.
    """
    if format == "xlsx" and not XLSX_AVAILABLE:
        raise HTTPException(status_code=400, detail="Format XLSX non disponible sur ce serveur.")

    # Mêmes validations que get_pivot
    require_entity_access(session=session, user=user, entity_id=entity_id)

    sc = session.get(ForecastScenario, scenario_id)
    if sc is None:
        raise HTTPException(status_code=404, detail="Scénario introuvable")
    if sc.entity_id != entity_id:
        raise HTTPException(status_code=403, detail="Scénario non rattaché à cette entité")

    from_month = _parse_year_month(from_, "from")
    to_month = _parse_year_month(to, "to")
    if from_month > to_month:
        raise HTTPException(status_code=400, detail="La borne 'from' doit être <= 'to'")
    span = _months_between(from_month, to_month)
    if span > _MAX_RANGE_MONTHS:
        raise HTTPException(status_code=400, detail=f"Plage trop large : {span} mois (maximum {_MAX_RANGE_MONTHS})")

    account_ids = _parse_accounts_csv(accounts)
    if account_ids is not None:
        entity_account_ids = set(
            session.scalars(select(BankAccount.id).where(BankAccount.entity_id == entity_id))
        )
        invalid = [a for a in account_ids if a not in entity_account_ids]
        if invalid:
            raise HTTPException(status_code=400, detail=f"Comptes non rattachés à l'entité : {invalid}")

    result = compute_pivot(
        session,
        scenario_id=scenario_id,
        entity_id=entity_id,
        from_month=from_month,
        to_month=to_month,
        account_ids=account_ids,
    )

    months = result.months

    # En-têtes : Catégorie, Niveau, Direction, puis pour chaque mois : Réalisé/Engagé/Prévisionnel
    base_headers = ["Categorie", "Niveau", "Direction"]
    month_headers = []
    for m in months:
        month_headers += [f"{m} Realise (EUR)", f"{m} Engage (EUR)", f"{m} Previsionnel (EUR)"]
    headers = base_headers + month_headers

    csv_rows = []
    for row in result.rows:
        base = [row.label, str(row.level), row.direction]
        for cell in row.cells:
            base += [
                f"{cell.realized_cents / 100:.2f}",
                f"{cell.committed_cents / 100:.2f}",
                f"{cell.forecast_cents / 100:.2f}",
            ]
        csv_rows.append(base)

    today = date.today().isoformat()
    filename_base = f"previsionnel-pivot_{today}"
    try:
        return export_response(headers, csv_rows, filename_base, format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
