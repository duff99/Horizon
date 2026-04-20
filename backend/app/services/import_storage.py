"""Stockage physique des PDFs importés.

Les fichiers sont stockés à `{IMPORT_STORAGE_PATH}/{sha256}.pdf`.
Le sha256 sert de clé naturelle : deux imports identiques partagent le même
fichier sur disque, et on retrouve le PDF depuis le ImportRecord via file_sha256.
"""
from __future__ import annotations

import os
from pathlib import Path

IMPORT_STORAGE_PATH = Path(os.getenv("IMPORT_STORAGE_PATH", "/data/imports"))


def _ensure_dir() -> None:
    IMPORT_STORAGE_PATH.mkdir(parents=True, exist_ok=True)


def file_path_for(file_sha256: str) -> Path:
    return IMPORT_STORAGE_PATH / f"{file_sha256}.pdf"


def save_pdf(file_sha256: str, data: bytes) -> Path:
    """Persiste le PDF sur disque de manière atomique.

    Retourne le chemin final. Idempotent : si le fichier existe déjà (même sha),
    on ne réécrit pas (même contenu par définition du sha).
    """
    _ensure_dir()
    dest = file_path_for(file_sha256)
    if dest.exists():
        return dest
    tmp = dest.with_suffix(".pdf.tmp")
    tmp.write_bytes(data)
    tmp.replace(dest)
    return dest


def read_pdf(file_sha256: str) -> bytes | None:
    """Retourne le PDF ou None s'il n'a pas été persisté."""
    p = file_path_for(file_sha256)
    if not p.exists():
        return None
    return p.read_bytes()
