"""Interface commune des analyseurs de relevés bancaires."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass
class ParsedTransaction:
    """Une transaction extraite d'un relevé, avant insertion en base."""
    operation_date: date
    value_date: date
    label: str                  # libellé normalisé (1 ligne, espaces compacts)
    raw_label: str              # libellé brut (multi-lignes possibles, joint par \n)
    amount: Decimal             # signé : > 0 encaissement, < 0 décaissement
    statement_row_index: int    # position dans le relevé (pour dédup stable)
    children: list["ParsedTransaction"] = field(default_factory=list)
    counterparty_hint: str | None = None  # nom extrait, avant normalisation

    @property
    def is_debit(self) -> bool:
        return self.amount < 0

    @property
    def is_credit(self) -> bool:
        return self.amount > 0

    @property
    def is_aggregation_parent(self) -> bool:
        return bool(self.children)


@dataclass
class ParsedStatement:
    """Résultat d'un parse() : métadonnées de compte + liste de transactions."""
    bank_code: str
    account_number: str
    iban: str | None
    period_start: date | None
    period_end: date | None
    opening_balance: Decimal | None
    closing_balance: Decimal | None
    transactions: list[ParsedTransaction]
    page_count: int = 0   # nombre de pages PDF, utilisé pour check_pages_limit

    @property
    def total_count(self) -> int:
        """Nombre total de lignes logiques (parents + enfants)."""
        count = 0
        for t in self.transactions:
            count += 1 + len(t.children)
        return count


class BaseParser(ABC):
    """Interface que chaque analyseur de banque doit implémenter."""

    bank_name: str   # "Delubac", "Qonto", …
    bank_code: str   # "delubac", "qonto", …

    @abstractmethod
    def detect(self, pdf_bytes: bytes) -> bool:
        """Retourne True si ce PDF ressemble à un relevé émis par cette banque."""

    @abstractmethod
    def parse(self, pdf_bytes: bytes) -> ParsedStatement:
        """Extrait un ParsedStatement du PDF."""
