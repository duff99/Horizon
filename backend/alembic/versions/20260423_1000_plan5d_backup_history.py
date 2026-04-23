"""Plan 5d : backup_history table pour traçabilité des backups.

Revision ID: e1f2a3b4c5d6
Revises: 6248434b2946
Create Date: 2026-04-23 10:00:00

Contexte : suite à l'incident de perte de données Astreos du 2026-04-21,
on introduit une procédure de backup rigoureuse avec traçabilité DB.
Chaque exécution de `backup-db.sh` insère une ligne ici ; `verify-restore.sh`
met à jour `verified_at` quand le round-trip est validé.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "e1f2a3b4c5d6"
down_revision = "6248434b2946"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.create_table(
        "backup_history",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
        ),
        sa.Column("file_path", sa.Text, nullable=False),
        sa.Column("size_bytes", sa.BigInteger, nullable=True),
        sa.Column("sha256", sa.CHAR(64), nullable=True),
        sa.Column(
            "row_counts_json",
            sa.dialects.postgresql.JSONB,
            nullable=True,
        ),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('running', 'success', 'failed', 'verified')",
            name="ck_backup_history_status",
        ),
    )
    op.create_index(
        "ix_backup_history_started_at",
        "backup_history",
        ["started_at"],
    )
    op.create_index(
        "ix_backup_history_status",
        "backup_history",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_backup_history_status", table_name="backup_history")
    op.drop_index("ix_backup_history_started_at", table_name="backup_history")
    op.drop_table("backup_history")
