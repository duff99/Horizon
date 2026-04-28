"""Étend backup_history pour la page UI Sauvegardes : type, error_step,
imports_size_bytes, imports_sha256, status='pending'.

Revision ID: f3d2c1b0a987
Revises: c1e7f0a4b8d9
Create Date: 2026-04-28 15:30:00

Permet :
- de distinguer les backups (scheduled / manual / pre-op / restore-test)
- de suivre la queue des triggers (status='pending' = demande UI en attente)
- d'afficher la taille du tar imports en plus du dump DB
- d'afficher l'étape précise d'un échec

Backfill : tous les rows existants reçoivent type='scheduled' (cron 2h).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "f3d2c1b0a987"
down_revision = "c1e7f0a4b8d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Ajouter colonnes (NULL temporairement pour le backfill)
    op.add_column("backup_history", sa.Column("type", sa.String(20), nullable=True))
    op.add_column("backup_history", sa.Column("error_step", sa.Text, nullable=True))
    op.add_column(
        "backup_history",
        sa.Column("imports_size_bytes", sa.BigInteger, nullable=True),
    )
    op.add_column(
        "backup_history",
        sa.Column("imports_sha256", sa.CHAR(64), nullable=True),
    )

    # 2. Backfill type pour les rows existants (cron quotidien historique)
    op.execute("UPDATE backup_history SET type = 'scheduled' WHERE type IS NULL")

    # 3. Rendre type NOT NULL après backfill
    op.alter_column("backup_history", "type", nullable=False)

    # 4. Index sur type (utile pour filtrage UI : restore-test, manual, etc.)
    op.create_index("ix_backup_history_type", "backup_history", ["type"])

    # 5. Étendre la check constraint status pour ajouter 'pending' (queue trigger)
    op.drop_constraint(
        "ck_backup_history_status", "backup_history", type_="check"
    )
    op.create_check_constraint(
        "ck_backup_history_status",
        "backup_history",
        "status IN ('pending', 'running', 'success', 'failed', 'verified')",
    )

    # 6. Check constraint type
    op.create_check_constraint(
        "ck_backup_history_type",
        "backup_history",
        "type IN ('scheduled', 'manual', 'pre-op', 'restore-test')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_backup_history_type", "backup_history", type_="check")
    op.drop_constraint(
        "ck_backup_history_status", "backup_history", type_="check"
    )
    op.create_check_constraint(
        "ck_backup_history_status",
        "backup_history",
        "status IN ('running', 'success', 'failed', 'verified')",
    )
    op.drop_index("ix_backup_history_type", table_name="backup_history")
    op.drop_column("backup_history", "imports_sha256")
    op.drop_column("backup_history", "imports_size_bytes")
    op.drop_column("backup_history", "error_step")
    op.drop_column("backup_history", "type")
