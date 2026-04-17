"""Erreurs levées par les analyseurs de relevés bancaires."""
from __future__ import annotations


class ParserError(Exception):
    """Base de toutes les erreurs des parsers."""


class UnknownBankError(ParserError):
    """Aucun parser n'a pu détecter la banque émettrice du PDF."""

    def __init__(self, message: str = "Banque inconnue — impossible de détecter l'émetteur") -> None:
        super().__init__(message)


class InvalidPdfStructureError(ParserError):
    """Le PDF est de la bonne banque mais sa structure interne est inattendue."""

    def __init__(self, message: str, *, page: int | None = None) -> None:
        super().__init__(message)
        self.page = page

    def __repr__(self) -> str:
        return f"InvalidPdfStructureError({self.args[0]!r}, page={self.page})"
