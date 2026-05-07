"""F1 — Index sur les FK sans index.

Revision ID: h0r1z0nf0100
Revises: h0r1z0n50802
Create Date: 2026-05-07 11:00:00
"""
from __future__ import annotations
from alembic import op

revision = "h0r1z0nf0100"
down_revision = "h0r1z0n50802"
branch_labels = None
depends_on = None

# Liste établie d'après la requête pg_constraint exécutée en live le 2026-05-07.
# forecast_entries est exclue (droppée par D1).
# Priorité haute : colonnes utilisées dans des requêtes fréquentes de production.
# Priorité normale : colonnes utilisées dans les DELETE/UPDATE en cascade.
_INDEXES = [
    # Priorité haute
    ("ix_transactions_import_id",                "transactions",           "import_id"),
    ("ix_transactions_categorization_rule_id",   "transactions",           "categorization_rule_id"),
    ("ix_commitments_category_id",               "commitments",            "category_id"),
    ("ix_commitments_counterparty_id",           "commitments",            "counterparty_id"),
    ("ix_commitments_bank_account_id",           "commitments",            "bank_account_id"),
    # Priorité normale
    ("ix_commitments_created_by_id",             "commitments",            "created_by_id"),
    ("ix_commitments_pdf_attachment_id",         "commitments",            "pdf_attachment_id"),
    ("ix_entities_parent_entity_id",             "entities",               "parent_entity_id"),
    ("ix_categories_parent_category_id",         "categories",             "parent_category_id"),
    ("ix_imports_uploaded_by_id",                "imports",                "uploaded_by_id"),
    ("ix_transactions_counter_entity_id",        "transactions",           "counter_entity_id"),
    ("ix_transactions_parent_transaction_id",    "transactions",           "parent_transaction_id"),
    ("ix_rules_bank_account_id",                 "categorization_rules",   "bank_account_id"),
    ("ix_rules_category_id",                     "categorization_rules",   "category_id"),
    ("ix_rules_counterparty_id",                 "categorization_rules",   "counterparty_id"),
    ("ix_rules_created_by_id",                   "categorization_rules",   "created_by_id"),
    ("ix_forecast_scenarios_created_by_id",      "forecast_scenarios",     "created_by_id"),
    ("ix_forecast_lines_base_category_id",       "forecast_lines",         "base_category_id"),
    ("ix_forecast_lines_updated_by_id",          "forecast_lines",         "updated_by_id"),
]


def upgrade() -> None:
    for index_name, table_name, col_name in _INDEXES:
        op.create_index(index_name, table_name, [col_name])


def downgrade() -> None:
    for index_name, table_name, _col in _INDEXES:
        op.drop_index(index_name, table_name=table_name)
