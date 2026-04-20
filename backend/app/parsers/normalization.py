"""Helpers de normalisation pour les parsers."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation

_WHITESPACE_RE = re.compile(r"\s+")


def fr_amount_to_decimal(s: str) -> Decimal:
    """Convertit un montant au format français ('1.234,56' ou '0,10') en Decimal.

    Raises:
        ValueError: si la chaîne n'est pas un montant valide.
    """
    cleaned = s.strip().replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"Montant invalide: {s!r}") from exc


def fr_date_to_date(s: str) -> date:
    """Convertit 'DD/MM/YYYY' en date."""
    parts = s.strip().split("/")
    if len(parts) != 3:
        raise ValueError(f"Date invalide: {s!r}")
    d, m, y = parts
    return date(int(y), int(m), int(d))


def fix_latin1_encoding(text: str) -> str:
    """Corrige le mojibake typique (texte latin-1 interprété comme utf-8).

    Exemple : 'IntÃ©rÃªts' → 'Intérêts'.

    Stratégie : si le texte contient des séquences typiques de mojibake
    (Ã©, Ã¨, Ã¢, etc.), ré-encoder en latin-1 puis décoder en utf-8.
    Sinon : retourner tel quel.
    """
    mojibake_markers = ("Ã©", "Ã¨", "Ãª", "Ã ", "Ã¢", "Ã§", "Ã´", "Ã»", "Ã®", "Ã¯")
    if not any(m in text for m in mojibake_markers):
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def normalize_label(raw: str) -> str:
    """Normalise un libellé pour les matchings et le dédoublonnage.

    - Supprime les diacritiques (café → CAFE)
    - Supprime la ponctuation sauf chiffres, lettres, espaces
    - Majuscule
    - Compacte les espaces
    """
    if raw is None:
        return ""
    text = raw.strip()
    # Normalisation Unicode NFD + suppression des marques de combinaison
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    # Upper
    text = text.upper()
    # Garder lettres latines, chiffres, espaces et traits d'union
    text = re.sub(r"[^A-Z0-9\s-]", " ", text)
    # Compacter les espaces
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


_COUNTERPARTY_RULES: list[tuple[re.Pattern[str], int]] = [
    # Lignes COMMISSION/TVA VIR SEPA → prendre ce qui vient après "VIR SEPA"
    (re.compile(r"^(?:COMMISSION|TVA)\s+VIR\s+SEPA\s+(.+)$", re.I), 1),
    # VIR SEPA <nom>
    (re.compile(r"^VIR\s+SEPA\s+(.+?)(?:\s+[A-Z]{3,}\s*\d.*)?$", re.I), 1),
    # PRLV SEPA <nom>
    (re.compile(r"^PRLV\s+SEPA\s+(.+?)(?:\s+[A-Z]{2,}\d.*)?$", re.I), 1),
    # CARTE DD/MM <nom>
    (re.compile(r"^CARTE\s+\d{2}/\d{2}\s+(.+)$", re.I), 1),
    # Crédit Agricole : "Carte X2043 <merchant> DD/MM"
    (re.compile(r"^Carte\s+[A-Z]?\d+\s+(.+?)\s+\d{2}/\d{2}\s*$", re.I), 1),
    # Crédit Agricole : "Virement [Web|Vir Inst vers|Recu de|de|vers] <name>"
    (
        re.compile(
            r"^Virement\s+(?:Web|Vir\s+Inst(?:\s+vers)?|Recu\s+de|de|vers)\s+"
            r"(.+?)(?:\s+Notes\s+de\s+frais.*|\s+FR\d{2}.*)?$",
            re.I,
        ),
        1,
    ),
    # Crédit Agricole : "Prlv <name>" (hors PRLV SEPA déjà couvert)
    (re.compile(r"^Prlv\s+(?!SEPA\b)(.+?)(?:\s+FR\d{2}.*)?$", re.I), 1),
]


def extract_counterparty(raw_label: str) -> str | None:
    """Extrait la contrepartie depuis un libellé brut.

    Retourne None si aucune heuristique n'a matché.
    """
    if not raw_label:
        return None
    text = raw_label.strip()
    for pattern, group in _COUNTERPARTY_RULES:
        m = pattern.match(text)
        if m:
            candidate = m.group(group).strip()
            # Stripper les suffixes numériques courants (références, IDs)
            candidate = re.sub(r"\s+[A-Z0-9]{3,}-?\d+.*$", "", candidate).strip()
            if candidate:
                return candidate
    return None


def compute_dedup_key(
    *,
    bank_account_id: int,
    operation_date: date,
    value_date: date,
    amount: Decimal,
    normalized_label: str,
    statement_row_index: int,
) -> str:
    """Calcule la clé stable de dédoublonnage (SHA-256 hex)."""
    parts = [
        str(bank_account_id),
        operation_date.isoformat(),
        value_date.isoformat(),
        f"{amount:.2f}",
        normalized_label,
        str(statement_row_index),
    ]
    blob = "|".join(parts).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()
