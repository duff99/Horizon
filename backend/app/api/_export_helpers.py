"""Helpers internes pour la génération de réponses CSV (et XLSX si openpyxl dispo).

Utilisé uniquement par les endpoints d'export — pas exposé comme router.
"""
from __future__ import annotations

import csv
import io

from fastapi.responses import StreamingResponse

# openpyxl est optionnel : G11 CSV uniquement si absent.
try:
    import openpyxl as _openpyxl  # noqa: F401
    XLSX_AVAILABLE = True
except ImportError:
    XLSX_AVAILABLE = False


def csv_response(
    headers: list[str],
    rows: list[list],
    filename: str,
) -> StreamingResponse:
    """Génère une StreamingResponse CSV UTF-8 avec BOM (pour Excel Windows)."""
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    w.writerow(headers)
    w.writerows(rows)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue().encode("utf-8-sig")]),  # BOM pour Excel FR
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


def xlsx_response(
    headers: list[str],
    rows: list[list],
    filename: str,
) -> StreamingResponse:
    """Génère une StreamingResponse XLSX. Lève ImportError si openpyxl absent."""
    if not XLSX_AVAILABLE:
        raise ImportError("openpyxl non disponible")
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


def export_response(
    headers: list[str],
    rows: list[list],
    filename_base: str,
    fmt: str,
) -> StreamingResponse:
    """Sélectionne le format selon fmt ('csv' ou 'xlsx').

    Si fmt='xlsx' et openpyxl absent : lève ValueError (à intercepter dans
    l'endpoint pour retourner 400).
    """
    if fmt == "xlsx":
        if not XLSX_AVAILABLE:
            raise ValueError("Format XLSX non disponible sur ce serveur.")
        return xlsx_response(headers, rows, f"{filename_base}.xlsx")
    return csv_response(headers, rows, f"{filename_base}.csv")
