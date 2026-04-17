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
            raw_lines = self._extract_raw_lines(pdf)

        transactions = [self._raw_line_to_parsed(rl) for rl in raw_lines]
        transactions = self._merge_sepa_trios(transactions)
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

    # -------- extraction lignes --------
    _IGNORE_PREFIXES = (
        "total des opérations",
        "total des operations",
        "ancien solde",
        "nouveau solde",
        "page",
        '"t" tarification',
        "rg sdc",
        "rg :",
        "code ag",
        "relevé de compte",
        "releve de compte",
        "date opé",
        "date ope",
        "date d'arrêté",
        "date d'arrete",
        "numéro client",
        "numero client",
        "intitulé du compte",
        "intitule du compte",
        "numéro de compte",
        "numero de compte",
        "iban :",
        "sas acreed",
        "5 lotissement",
        "43320 saint-vidal",
        "votre gestionnaire",
        "internet :",
        "banque à distance",
    )

    def _extract_raw_lines(self, pdf: pdfplumber.PDF) -> list[_RawLine]:
        """Parcourt chaque page et reconstruit les lignes de transactions."""
        raw_lines: list[_RawLine] = []
        global_idx = 0
        for page_num, page in enumerate(pdf.pages, start=1):
            # On regroupe les mots par ligne (même top ± 1.5 px)
            words = page.extract_words(keep_blank_chars=False, x_tolerance=2,
                                       y_tolerance=3)
            rows = self._group_words_by_row(words)
            current: _RawLine | None = None
            for row in rows:
                # Filtrer en-têtes et pieds
                joined = " ".join(w["text"] for w in row).strip()
                low = joined.lower()
                if any(low.startswith(p) for p in self._IGNORE_PREFIXES):
                    if current is not None:
                        raw_lines.append(current)
                        current = None
                    continue
                first_text = row[0]["text"]
                if _TXN_DATE_RE.match(first_text):
                    # Nouvelle ligne de transaction : clôturer la précédente
                    if current is not None:
                        raw_lines.append(current)
                    try:
                        current = self._parse_txn_row(row, page_num, global_idx)
                        global_idx += 1
                    except ValueError:
                        current = None
                else:
                    # Ligne de détail : attacher au current
                    if current is not None:
                        current.detail_lines.append(
                            fix_latin1_encoding(joined).strip()
                        )
            # Fin de page : clôturer la ligne ouverte
            if current is not None:
                raw_lines.append(current)
                current = None
        return raw_lines

    @staticmethod
    def _group_words_by_row(words: list[dict]) -> list[list[dict]]:
        """Groupe les mots pdfplumber par ligne (y proche), ordonnés par x."""
        rows: dict[int, list[dict]] = {}
        for w in words:
            key = round(w["top"])
            # Fusion avec une ligne existante ± 2 px (gestion du bruit vertical)
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

    def _parse_txn_row(self, row: list[dict], page_num: int, row_index: int) -> _RawLine:
        """Décompose une ligne en (op_date, value_date, label, montant, colonne)."""
        op_date = fr_date_to_date(row[0]["text"])
        # Date valeur : 2e mot (fallback : même que op_date)
        try:
            val_date = fr_date_to_date(row[1]["text"])
            label_start = 2
        except (ValueError, IndexError):
            val_date = op_date
            label_start = 1

        # Montant : dernier mot, x1 ≈ 455 (débit) ou ≈ 550 (crédit)
        last = row[-1]
        try:
            magnitude = fr_amount_to_decimal(last["text"])
        except ValueError as exc:
            raise ValueError(f"Montant invalide: {last['text']!r}") from exc

        # Seuil : x1 < 470 → débit, sinon crédit
        is_debit = last["x1"] < 475
        signed_amount = -magnitude if is_debit else magnitude

        # Libellé : tous les mots entre label_start et avant le dernier (montant)
        label_words = row[label_start:-1]
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

    def _raw_line_to_parsed(self, rl: _RawLine) -> ParsedTransaction:
        """Convertit une ligne brute en ParsedTransaction (sans fusion SEPA)."""
        detail = " ".join(rl.detail_lines).strip()
        full_label = (rl.label + " " + detail).strip() if detail else rl.label
        full_label = re.sub(r"\s+", " ", full_label)
        return ParsedTransaction(
            operation_date=rl.operation_date,
            value_date=rl.value_date,
            label=full_label,
            raw_label=full_label,
            amount=rl.amount,
            statement_row_index=rl.row_index,
        )

    _COMMISSION_PREFIX = "COMMISSION VIR SEPA"
    _TVA_PREFIX = "TVA VIR SEPA"
    _VIR_PREFIX = "VIR SEPA"

    def _merge_sepa_trios(
        self, transactions: list[ParsedTransaction]
    ) -> list[ParsedTransaction]:
        """Fusionne les trios (VIR SEPA parent + COMMISSION + TVA) en transaction parente."""
        merged: list[ParsedTransaction] = []
        i = 0
        n = len(transactions)
        while i < n:
            t = transactions[i]
            # On fusionne uniquement si :
            # - t commence par "VIR SEPA " (hors COMMISSION/TVA)
            # - t est un débit
            # - i+1 commence par "COMMISSION VIR SEPA" sur même date
            # - i+2 commence par "TVA VIR SEPA" sur même date
            if (
                i + 2 < n
                and t.label.startswith(self._VIR_PREFIX + " ")
                and not t.label.startswith(self._COMMISSION_PREFIX)
                and not t.label.startswith(self._TVA_PREFIX)
                and t.amount < 0
                and transactions[i + 1].label.startswith(self._COMMISSION_PREFIX)
                and transactions[i + 1].operation_date == t.operation_date
                and transactions[i + 2].label.startswith(self._TVA_PREFIX)
                and transactions[i + 2].operation_date == t.operation_date
            ):
                parent_raw = t
                child_commission = transactions[i + 1]
                child_tva = transactions[i + 2]
                # L'ex-parent "VIR SEPA …" devient un enfant ; on crée un nouveau parent agrégé
                parent = ParsedTransaction(
                    operation_date=t.operation_date,
                    value_date=t.value_date,
                    label=parent_raw.label,
                    raw_label=parent_raw.raw_label,
                    amount=parent_raw.amount + child_commission.amount + child_tva.amount,
                    statement_row_index=parent_raw.statement_row_index,
                    children=[
                        ParsedTransaction(
                            operation_date=parent_raw.operation_date,
                            value_date=parent_raw.value_date,
                            label=parent_raw.label,
                            raw_label=parent_raw.raw_label,
                            amount=parent_raw.amount,
                            statement_row_index=parent_raw.statement_row_index,
                        ),
                        child_commission,
                        child_tva,
                    ],
                )
                merged.append(parent)
                i += 3
            else:
                merged.append(t)
                i += 1
        return merged

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
