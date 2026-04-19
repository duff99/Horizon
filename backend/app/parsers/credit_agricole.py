"""Analyseur des relevés bancaires Crédit Agricole (format standard)."""
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
    extract_counterparty,
    fix_latin1_encoding,
    fr_amount_to_decimal,
)

_DETECTION_MARKERS: Final = (
    b"CREDIT AGRICOLE",
    b"credit-agricole",
    b"AGRIFRPP",
)

_IBAN_RE = re.compile(r"IBAN\s*:\s*([A-Z0-9 ]{15,40}?)(?=\s+BIC\b|\s*$|\n)", re.M)
_ACCOUNT_NUM_RE = re.compile(r"Compte\s+Courant\s+n[°o]\s*(\d+)", re.I)
_ARRETE_RE = re.compile(
    r"Date\s+d[' ]arr[êe]t[ée]\s*:\s*(\d{1,2})\s+([A-Za-zÀ-ÿ]+)\s+(\d{4})",
    re.I,
)
_OPENING_RE = re.compile(
    r"Ancien\s+solde\s+(créditeur|débiteur|crditeur|debiteur)\s+au\s+"
    r"(\d{2}\.\d{2}\.\d{4})\s+([\d ]+,\d{2})",
    re.I,
)
_CLOSING_RE = re.compile(
    r"Nouveau\s+solde\s+(créditeur|débiteur|crditeur|debiteur)\s+au\s+"
    r"(\d{2}\.\d{2}\.\d{4})\s+([\d ]+,\d{2})",
    re.I,
)
_SHORT_DATE_RE = re.compile(r"^\d{2}\.\d{2}$")
_AMOUNT_TAIL_RE = re.compile(r"^[\d ]+,\d{2}$")

_FR_MONTHS = {
    "janvier": 1, "fevrier": 2, "février": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "aout": 8, "août": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12, "décembre": 12,
}

_DEBIT_X1_THRESHOLD: Final = 500.0
_TRAILING_NOISE: Final = ("¨", "þ", "☐", "□")


@dataclass
class _RawLine:
    operation_date: date
    value_date: date
    label: str
    detail_lines: list[str]
    amount: Decimal
    page: int
    row_index: int


class CreditAgricoleParser(BaseParser):
    bank_name = "Crédit Agricole"
    bank_code = "credit_agricole"

    def detect(self, pdf_bytes: bytes) -> bool:
        if not pdf_bytes.startswith(b"%PDF"):
            return False
        head = pdf_bytes[:300_000]
        if any(marker in head for marker in _DETECTION_MARKERS):
            return True
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                if not pdf.pages:
                    return False
                text = pdf.pages[0].extract_text() or ""
                return "CREDIT AGRICOLE" in text.upper() and "RELEVE" in text.upper()
        except Exception:
            return False

    def parse(self, pdf_bytes: bytes) -> ParsedStatement:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            full_text = "\n".join(
                fix_latin1_encoding(p.extract_text() or "") for p in pdf.pages
            )
            account_number, iban = self._parse_account_identifiers(full_text)
            stmt_year, stmt_month = self._parse_arrete(full_text)
            opening_balance, opening_date = self._parse_opening_balance(full_text)
            closing_balance, closing_date = self._parse_closing_balance(full_text)
            raw_lines = self._extract_raw_lines(pdf, stmt_year, stmt_month)

        transactions = [self._raw_line_to_parsed(rl) for rl in raw_lines]
        period_start, period_end = self._period_from_transactions(
            transactions, opening_date, closing_date
        )

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

    def _parse_account_identifiers(self, text: str) -> tuple[str, str | None]:
        num_m = _ACCOUNT_NUM_RE.search(text)
        if not num_m:
            raise InvalidPdfStructureError("Numéro de compte introuvable")
        account_number = num_m.group(1).strip()
        iban_m = _IBAN_RE.search(text)
        iban = iban_m.group(1).replace(" ", "") if iban_m else None
        return account_number, iban

    def _parse_arrete(self, text: str) -> tuple[int, int]:
        m = _ARRETE_RE.search(text)
        if not m:
            raise InvalidPdfStructureError("Date d'arrêté introuvable")
        month_name = m.group(2).lower()
        month = _FR_MONTHS.get(month_name)
        if month is None:
            raise InvalidPdfStructureError(f"Mois inconnu : {month_name}")
        year = int(m.group(3))
        return year, month

    def _parse_opening_balance(self, text: str) -> tuple[Decimal | None, date | None]:
        m = _OPENING_RE.search(text)
        if not m:
            return None, None
        amt = fr_amount_to_decimal(m.group(3))
        if "débiteur" in m.group(1).lower() or "debiteur" in m.group(1).lower():
            amt = -amt
        d, mo, y = m.group(2).split(".")
        return amt, date(int(y), int(mo), int(d))

    def _parse_closing_balance(self, text: str) -> tuple[Decimal | None, date | None]:
        m = _CLOSING_RE.search(text)
        if not m:
            return None, None
        amt = fr_amount_to_decimal(m.group(3))
        if "débiteur" in m.group(1).lower() or "debiteur" in m.group(1).lower():
            amt = -amt
        d, mo, y = m.group(2).split(".")
        return amt, date(int(y), int(mo), int(d))

    _IGNORE_PREFIXES = (
        "total des opérations", "total des operations",
        "ancien solde", "nouveau solde",
        "page", "date d'arrêté", "date d'arrete",
        "date date libellé", "date date libelle",
        "opé. valeur", "ope. valeur",
        "iban :", "synthese", "synthèse",
        "votre agence", "votre conseiller", "vos contacts",
        "relevé de comptes", "releve de comptes",
        "compte courant n°", "compte courant no",
        "s.a.s.", "s.a.r.l.", "5 lotissement",
        "tél :", "tel :", "appli mobile", "agence en ligne",
        "loire haute-loire", "pe haute loire",
    )

    def _extract_raw_lines(
        self, pdf: pdfplumber.PDF, stmt_year: int, stmt_month: int
    ) -> list[_RawLine]:
        raw_lines: list[_RawLine] = []
        global_idx = 0
        for page_num, page in enumerate(pdf.pages, start=1):
            words = page.extract_words(
                keep_blank_chars=False, x_tolerance=2, y_tolerance=3,
            )
            # Strip left-margin artifacts (page/bookmark numbers at x0 < 15)
            words = [w for w in words if w["x0"] >= 15]
            rows = self._group_words_by_row(words)
            current: _RawLine | None = None
            for row in rows:
                joined = " ".join(w["text"] for w in row).strip()
                low = joined.lower()
                if any(low.startswith(p) for p in self._IGNORE_PREFIXES):
                    if current is not None:
                        raw_lines.append(current)
                        current = None
                    continue

                first_text = row[0]["text"]
                if _SHORT_DATE_RE.match(first_text):
                    if current is not None:
                        raw_lines.append(current)
                        current = None
                    try:
                        current = self._parse_txn_row(
                            row, page_num, global_idx, stmt_year, stmt_month,
                        )
                        global_idx += 1
                    except ValueError:
                        current = None
                else:
                    if current is not None:
                        current.detail_lines.append(
                            fix_latin1_encoding(joined).strip()
                        )
            if current is not None:
                raw_lines.append(current)
                current = None
        return raw_lines

    @staticmethod
    def _group_words_by_row(words: list[dict]) -> list[list[dict]]:
        rows: dict[int, list[dict]] = {}
        for w in words:
            key = round(w["top"])
            matched = None
            for k in rows:
                if abs(k - key) <= 2:
                    matched = k
                    break
            k = matched if matched is not None else key
            rows.setdefault(k, []).append(w)
        result = []
        for k in sorted(rows):
            result.append(sorted(rows[k], key=lambda w: w["x0"]))
        return result

    def _parse_txn_row(
        self,
        row: list[dict],
        page_num: int,
        row_index: int,
        stmt_year: int,
        stmt_month: int,
    ) -> _RawLine:
        # Strip trailing decorative markers (e.g. checkbox "¨") before parsing
        while row and row[-1]["text"] in _TRAILING_NOISE:
            row = row[:-1]

        op_date = self._short_date_to_date(
            row[0]["text"], stmt_year, stmt_month,
        )
        if len(row) >= 2 and _SHORT_DATE_RE.match(row[1]["text"]):
            val_date = self._short_date_to_date(
                row[1]["text"], stmt_year, stmt_month,
            )
            label_start = 2
        else:
            val_date = op_date
            label_start = 1

        magnitude, consumed = self._extract_trailing_amount(row)
        if magnitude is None:
            raise ValueError("Montant introuvable")

        last_word = row[-1]
        is_debit = last_word["x1"] < _DEBIT_X1_THRESHOLD
        signed_amount = -magnitude if is_debit else magnitude

        label_words = row[label_start : len(row) - consumed]
        label_raw = " ".join(w["text"] for w in label_words).strip()
        label_raw = fix_latin1_encoding(label_raw)

        return _RawLine(
            operation_date=op_date,
            value_date=val_date,
            label=label_raw,
            detail_lines=[],
            amount=signed_amount,
            page=page_num,
            row_index=row_index,
        )

    @staticmethod
    def _short_date_to_date(s: str, year: int, stmt_month: int) -> date:
        d_str, m_str = s.split(".")
        d = int(d_str)
        m = int(m_str)
        # Si tx dans un mois > mois de l'arrêté, alors c'est l'année précédente
        # (relevé de janvier mentionnant le 31/12 de l'année précédente).
        tx_year = year
        if m > stmt_month:
            tx_year = year - 1
        return date(tx_year, m, d)

    def _extract_trailing_amount(
        self, row: list[dict],
    ) -> tuple[Decimal | None, int]:
        """Récupère le montant en fin de ligne, en joignant les fragments
        séparés par un espace (ex: ['20', '403,60'] → '20403,60')."""
        if not row:
            return None, 0
        tail = row[-1]["text"]
        if not _AMOUNT_TAIL_RE.match(tail) and "," not in tail:
            return None, 0
        fragments = [tail]
        consumed = 1
        prev_x0 = row[-1]["x0"]
        for i in range(len(row) - 2, -1, -1):
            word = row[i]["text"]
            if re.fullmatch(r"\d+", word) and prev_x0 - row[i]["x1"] <= 5:
                fragments.insert(0, word)
                consumed += 1
                prev_x0 = row[i]["x0"]
            else:
                break
        joined = "".join(fragments)
        try:
            return fr_amount_to_decimal(joined), consumed
        except ValueError:
            return None, 0

    def _raw_line_to_parsed(self, rl: _RawLine) -> ParsedTransaction:
        detail = " ".join(rl.detail_lines).strip()
        full_label = (rl.label + " " + detail).strip() if detail else rl.label
        full_label = re.sub(r"\s+", " ", full_label)
        hint = extract_counterparty(rl.label)
        return ParsedTransaction(
            operation_date=rl.operation_date,
            value_date=rl.value_date,
            label=full_label,
            raw_label=full_label,
            amount=rl.amount,
            statement_row_index=rl.row_index,
            counterparty_hint=hint,
        )

    def _period_from_transactions(
        self,
        transactions: list[ParsedTransaction],
        opening_date: date | None,
        closing_date: date | None,
    ) -> tuple[date | None, date | None]:
        if not transactions:
            return opening_date, closing_date
        dates = [t.operation_date for t in transactions]
        return min(dates), max(dates)
