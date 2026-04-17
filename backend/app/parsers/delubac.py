"""Analyseur du relevé bancaire Delubac (format Mapping Suite)."""
from __future__ import annotations

import io
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Final

import pdfplumber

from app.parsers.base import BaseParser, ParsedStatement, ParsedTransaction
from app.parsers.errors import InvalidPdfStructureError
from app.parsers.normalization import (
    fix_latin1_encoding,
    fr_amount_to_decimal,
    fr_date_to_date,
    normalize_label,
)


_DETECTION_MARKERS: Final = (
    b"DELUFR22",
    b"Delubac",
    b"edelubac.com",
    b"map_809",
)

_IBAN_RE = re.compile(r"IBAN\s*:\s*([A-Z0-9 ]{15,40}?)(?=\s+BIC\b|\s*$|\n)", re.M)
_ACCOUNT_NUM_RE = re.compile(r"Num[ée]ro\s+de\s+compte\s*:\s*(\d+)")
_OPENING_RE = re.compile(
    r"Ancien\s+solde\s+au\s+(\d{2}/\d{2}/\d{4})\s+([\d.,-]+)",
    re.I,
)
_CLOSING_RE = re.compile(
    r"Nouveau\s+solde\s+(?:créditeur|débiteur|crditeur|debiteur)\s+au\s+(\d{2}/\d{2}/\d{4})\s+([\d.,-]+)",
    re.I,
)
_TXN_DATE_RE = re.compile(r"^\d{2}/\d{2}/\d{4}")


@dataclass
class _RawLine:
    """Une ligne de transaction brute (principale) avec ses lignes de détail."""
    operation_date: date
    value_date: date
    label: str                # libellé principal (1 ligne)
    detail_lines: list[str]   # lignes continues sous le libellé
    amount: Decimal           # signé : + crédit, − débit
    page: int
    row_index: int            # index global dans le relevé


class DelubacParser(BaseParser):
    bank_name = "Delubac"
    bank_code = "delubac"

    # -------- détection --------
    def detect(self, pdf_bytes: bytes) -> bool:
        if not pdf_bytes.startswith(b"%PDF"):
            return False
        head = pdf_bytes[:200_000]
        if any(marker in head for marker in _DETECTION_MARKERS):
            return True
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                if not pdf.pages:
                    return False
                text = pdf.pages[0].extract_text() or ""
                return "RELEVÉ DE COMPTE" in text and "DELUFR22" in text
        except Exception:
            return False

    # -------- parsing --------
    def parse(self, pdf_bytes: bytes) -> ParsedStatement:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            full_text = "\n".join(
                fix_latin1_encoding(p.extract_text() or "") for p in pdf.pages
            )
            account_number, iban = self._parse_account_identifiers(full_text)
            opening_balance, opening_date = self._parse_opening_balance(full_text)
            closing_balance, closing_date = self._parse_closing_balance(full_text)

            # Pour l'instant : pas de transactions — D3 les ajoute.
            transactions: list[ParsedTransaction] = []
            period_start, period_end = self._parse_period(full_text, opening_date, closing_date)

        return ParsedStatement(
            bank_code=self.bank_code,
            account_number=account_number,
            iban=iban,
            period_start=period_start,
            period_end=period_end,
            opening_balance=opening_balance,
            closing_balance=closing_balance,
            transactions=transactions,
        )

    # -------- helpers en-tête --------
    def _parse_account_identifiers(self, text: str) -> tuple[str, str | None]:
        num_m = _ACCOUNT_NUM_RE.search(text)
        if not num_m:
            raise InvalidPdfStructureError("Numéro de compte introuvable")
        account_number = num_m.group(1).strip()
        iban_m = _IBAN_RE.search(text)
        iban = iban_m.group(1).replace(" ", "") if iban_m else None
        return account_number, iban

    def _parse_opening_balance(self, text: str) -> tuple[Decimal | None, date | None]:
        m = _OPENING_RE.search(text)
        if not m:
            return None, None
        return fr_amount_to_decimal(m.group(2)), fr_date_to_date(m.group(1))

    def _parse_closing_balance(self, text: str) -> tuple[Decimal | None, date | None]:
        m = _CLOSING_RE.search(text)
        if not m:
            return None, None
        amt = fr_amount_to_decimal(m.group(2))
        # Débiteur = solde négatif
        if "débiteur" in m.group(0).lower() or "debiteur" in m.group(0).lower():
            amt = -amt
        return amt, fr_date_to_date(m.group(1))

    def _parse_period(self, text: str, opening_date: date | None,
                      closing_date: date | None) -> tuple[date | None, date | None]:
        # Pour les tests de D2, pas encore de transactions → on renvoie
        # les dates basées sur les lignes de transactions si présentes, sinon
        # les dates de soldes.
        txn_dates: list[date] = []
        for line in text.splitlines():
            m = _TXN_DATE_RE.match(line)
            if m:
                try:
                    txn_dates.append(fr_date_to_date(m.group(0)))
                except ValueError:
                    continue
        if txn_dates:
            return min(txn_dates), max(txn_dates)
        return opening_date, closing_date
