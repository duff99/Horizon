"""Snapshot mensuel du prévisionnel (figé pour comparaison prévu vs réalisé).

Revision ID: h0r1z0nm1800
Revises: h0r1z0nm1700
Create Date: 2026-05-12 18:00:00

Une cellule prévisionnelle calculée (AVG_3M, PREVIOUS_MONTH, FORMULA…)
donne une valeur DIFFÉRENTE selon le moment où on la consulte (l'historique
sous-jacent évolue). Pour permettre une comparaison stable « prévu vs
réalisé », on fige la valeur prédite d'un mois quand celui-ci devient
passé. C'est ce snapshot qu'on compare aux transactions réelles importées.

Indexé sur (scenario_id, month) pour les requêtes de comparaison plage.
Unique sur (scenario_id, category_id, month) — un seul snapshot par
cellule ; un "Re-clôturer" remplace via UPSERT.
"""
from alembic import op
import sqlalchemy as sa


revision = "h0r1z0nm1800"
down_revision = "h0r1z0nm1700"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "forecast_month_snapshots",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "scenario_id",
            sa.Integer,
            sa.ForeignKey("forecast_scenarios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "category_id",
            sa.Integer,
            sa.ForeignKey("categories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("month", sa.Date, nullable=False),  # 1er du mois
        sa.Column("forecast_cents", sa.Integer, nullable=False),
        sa.Column(
            "is_auto",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "scenario_id",
            "category_id",
            "month",
            name="uq_forecast_snapshot_scenario_category_month",
        ),
    )
    op.create_index(
        "ix_forecast_snapshot_scenario_month",
        "forecast_month_snapshots",
        ["scenario_id", "month"],
    )


def downgrade() -> None:
    op.drop_index("ix_forecast_snapshot_scenario_month", "forecast_month_snapshots")
    op.drop_table("forecast_month_snapshots")
