"""Autorise plusieurs ForecastLine par (scenario, category).

Revision ID: h0r1z0nm1700
Revises: h0r1z0ng1200
Create Date: 2026-05-12 17:00:00

Avant : `UNIQUE (scenario_id, category_id)` → une seule règle par couple,
chaque upsert écrasait la précédente. Cas cassé : saisir un montant
ponctuel sur Mai puis un récurrent à partir de Juin écrasait Mai.

Après : `UNIQUE (scenario_id, category_id, COALESCE(start_month,…),
COALESCE(end_month,…))` → plusieurs règles autorisées tant qu'elles n'ont
pas exactement la même fenêtre. Les chevauchements sont permis ; le
moteur de calcul choisit la règle la plus spécifique pour chaque mois.

Migration data-friendly : les lignes existantes restent valides telles
quelles, elles deviennent juste "modifiables ou complétables" au lieu
d'être remplacées à chaque save.
"""
from alembic import op


revision = "h0r1z0nm1700"
down_revision = "h0r1z0ng1200"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_forecast_line_scenario_category",
        "forecast_lines",
        type_="unique",
    )
    # Postgres considère NULL != NULL dans une contrainte UNIQUE classique,
    # donc on encadre via COALESCE pour qu'une fenêtre "ouverte" (NULL/NULL)
    # ne se duplique pas non plus.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_forecast_line_scenario_category_window
        ON forecast_lines (
            scenario_id,
            category_id,
            COALESCE(start_month, DATE '1900-01-01'),
            COALESCE(end_month, DATE '9999-12-31')
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_forecast_line_scenario_category_window;")
    op.create_unique_constraint(
        "uq_forecast_line_scenario_category",
        "forecast_lines",
        ["scenario_id", "category_id"],
    )
