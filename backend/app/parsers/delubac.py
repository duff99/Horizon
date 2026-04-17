"""Analyseur du relevé bancaire Delubac (format Mapping Suite)."""
from __future__ import annotations

import io
from typing import Final

import pdfplumber

from app.parsers.base import BaseParser, ParsedStatement
from app.parsers.errors import InvalidPdfStructureError


_DETECTION_MARKERS: Final = (
    b"DELUFR22",          # BIC Delubac
    b"Delubac",           # mention "Banque Delubac" ou www.delubac.com
    b"edelubac.com",
    b"map_809",           # Creator PDF des relevés Delubac
)


class DelubacParser(BaseParser):
    bank_name = "Delubac"
    bank_code = "delubac"

    def detect(self, pdf_bytes: bytes) -> bool:
        """Détection par présence de marqueurs Delubac dans le PDF brut."""
        if not pdf_bytes.startswith(b"%PDF"):
            return False
        # Test rapide bytes sans parser le PDF complet
        head = pdf_bytes[:200_000]  # premiers ~200 Ko suffisent
        if any(marker in head for marker in _DETECTION_MARKERS):
            return True
        # Fallback : extraire la 1ère page et chercher les en-têtes textuels
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                if not pdf.pages:
                    return False
                text = pdf.pages[0].extract_text() or ""
                return "RELEVÉ DE COMPTE" in text and "DELUFR22" in text
        except Exception:
            return False

    def parse(self, pdf_bytes: bytes) -> ParsedStatement:
        raise NotImplementedError  # implémenté en D2-D5
