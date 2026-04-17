"""Module d'analyseurs de relevés bancaires avec registre."""
from __future__ import annotations

from app.parsers.base import BaseParser, ParsedStatement, ParsedTransaction
from app.parsers.errors import (
    InvalidPdfStructureError,
    ParserError,
    UnknownBankError,
)

_REGISTRY: dict[str, BaseParser] = {}


def register_parser(parser: BaseParser) -> None:
    """Enregistre un parser dans le registre global. Lève ValueError si doublon."""
    code = parser.bank_code
    if code in _REGISTRY:
        raise ValueError(f"Parser for bank_code={code!r} is already registered")
    _REGISTRY[code] = parser


def get_registry() -> dict[str, BaseParser]:
    """Retourne le registre (mutable — usage test uniquement)."""
    return _REGISTRY


def get_parser_by_code(bank_code: str) -> BaseParser:
    """Retourne le parser enregistré pour `bank_code`. Lève UnknownBankError."""
    if bank_code not in _REGISTRY:
        raise UnknownBankError(f"Aucun parser pour bank_code={bank_code!r}")
    return _REGISTRY[bank_code]


def get_parser_for(pdf_bytes: bytes) -> BaseParser:
    """Détecte la banque via `.detect()` de chaque parser enregistré."""
    for parser in _REGISTRY.values():
        if parser.detect(pdf_bytes):
            return parser
    raise UnknownBankError()


def _auto_register() -> None:
    """Importe les modules parsers connus pour qu'ils s'enregistrent.

    Convention : chaque fichier parser (ex. `delubac.py`) instancie et enregistre
    son parser via `register_parser(...)` au niveau module.
    """
    from app.parsers import delubac  # noqa: F401  (import pour side-effect)


__all__ = [
    "BaseParser", "ParsedStatement", "ParsedTransaction",
    "ParserError", "UnknownBankError", "InvalidPdfStructureError",
    "register_parser", "get_parser_for", "get_parser_by_code", "get_registry",
]
