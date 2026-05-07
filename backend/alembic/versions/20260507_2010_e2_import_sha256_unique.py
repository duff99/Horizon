"""E2 — Contrainte unique (bank_account_id, file_sha256) sur imports.

Revision ID: h0r1z0ne0200
Revises: h0r1z0ne0100
Create Date: 2026-05-07 20:10:00

Ajoute un index unique partiel (file_sha256 IS NOT NULL) pour éviter
les doublons d'import du même fichier PDF sur le même compte bancaire.
Idempotent via IF NOT EXISTS.

La table s'appelle 'imports' (pas 'import_records').
"""
from __future__ import annotations

from alembic import op

revision = "h0r1z0ne0200"
down_revision = "h0r1z0ne0100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_imports_account_sha256",
        "imports",
        ["bank_account_id", "file_sha256"],
        unique=True,
        postgresql_where="file_sha256 IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_index("uq_imports_account_sha256", table_name="imports")
