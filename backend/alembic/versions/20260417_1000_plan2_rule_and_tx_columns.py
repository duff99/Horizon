"""Plan 2 B1 : categorization_rules table + transaction categorization columns.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-17 10:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import unicodedata
import re


revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def _normalize_py(raw: str) -> str:
    """Réplique EXACTEMENT app.parsers.normalization.normalize_label pour le backfill."""
    if raw is None:
        return ""
    text = raw.strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.upper()
    text = re.sub(r"[^A-Z0-9\s-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def upgrade() -> None:
    rule_label_op = sa.Enum(
        "CONTAINS", "STARTS_WITH", "ENDS_WITH", "EQUALS",
        name="rule_label_operator",
    )
    rule_amount_op = sa.Enum(
        "EQ", "NE", "GT", "LT", "BETWEEN",
        name="rule_amount_operator",
    )
    rule_direction = sa.Enum(
        "CREDIT", "DEBIT", "ANY",
        name="rule_direction",
    )
    tx_cat_source = sa.Enum(
        "NONE", "RULE", "MANUAL",
        name="transaction_categorization_source",
    )
    rule_label_op.create(op.get_bind(), checkfirst=True)
    rule_amount_op.create(op.get_bind(), checkfirst=True)
    rule_direction.create(op.get_bind(), checkfirst=True)
    tx_cat_source.create(op.get_bind(), checkfirst=True)

    # Réutilise les enums sans les recréer dans les CREATE TABLE / ADD COLUMN
    rule_label_op_ref = postgresql.ENUM(
        "CONTAINS", "STARTS_WITH", "ENDS_WITH", "EQUALS",
        name="rule_label_operator", create_type=False,
    )
    rule_amount_op_ref = postgresql.ENUM(
        "EQ", "NE", "GT", "LT", "BETWEEN",
        name="rule_amount_operator", create_type=False,
    )
    rule_direction_ref = postgresql.ENUM(
        "CREDIT", "DEBIT", "ANY",
        name="rule_direction", create_type=False,
    )
    tx_cat_source_ref = postgresql.ENUM(
        "NONE", "RULE", "MANUAL",
        name="transaction_categorization_source", create_type=False,
    )

    op.create_table(
        "categorization_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("entity_id", sa.Integer(),
                  sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        sa.Column("label_operator", rule_label_op_ref, nullable=True),
        sa.Column("label_value", sa.String(200), nullable=True),
        sa.Column("direction", rule_direction_ref, nullable=False,
                  server_default="ANY"),
        sa.Column("amount_operator", rule_amount_op_ref, nullable=True),
        sa.Column("amount_value", sa.Numeric(14, 2), nullable=True),
        sa.Column("amount_value2", sa.Numeric(14, 2), nullable=True),
        sa.Column("counterparty_id", sa.Integer(),
                  sa.ForeignKey("counterparties.id", ondelete="SET NULL"), nullable=True),
        sa.Column("bank_account_id", sa.Integer(),
                  sa.ForeignKey("bank_accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("category_id", sa.Integer(),
                  sa.ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_by_id", sa.Integer(),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.CheckConstraint(
            "(amount_operator IS NULL) OR (amount_value IS NOT NULL)",
            name="ck_rule_amount_value_required",
        ),
        sa.CheckConstraint(
            "(amount_operator <> 'BETWEEN') OR "
            "(amount_value2 IS NOT NULL AND amount_value < amount_value2)",
            name="ck_rule_between_coherent",
        ),
        sa.CheckConstraint(
            "(label_operator IS NULL) OR (label_value IS NOT NULL AND length(label_value) >= 1)",
            name="ck_rule_label_value_required",
        ),
        sa.CheckConstraint(
            "(label_operator IS NOT NULL "
            "OR counterparty_id IS NOT NULL "
            "OR bank_account_id IS NOT NULL "
            "OR amount_operator IS NOT NULL "
            "OR direction <> 'ANY')",
            name="ck_rule_at_least_one_filter",
        ),
    )
    op.create_index(
        "uq_rule_priority_per_scope",
        "categorization_rules",
        [sa.text("COALESCE(entity_id, 0)"), "priority"],
        unique=True,
    )
    op.create_index(
        "ix_rule_entity_priority",
        "categorization_rules",
        ["entity_id", "priority"],
    )

    op.add_column(
        "transactions",
        sa.Column("normalized_label", sa.String(500), nullable=False,
                  server_default=""),
    )
    op.add_column(
        "transactions",
        sa.Column("categorized_by", tx_cat_source_ref, nullable=False,
                  server_default="NONE"),
    )
    op.add_column(
        "transactions",
        sa.Column("categorization_rule_id", sa.Integer(),
                  sa.ForeignKey("categorization_rules.id", ondelete="SET NULL"),
                  nullable=True),
    )
    op.create_index("ix_tx_normalized_label", "transactions", ["normalized_label"])
    op.create_index("ix_tx_categorized_by", "transactions", ["categorized_by"])

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, label FROM transactions")).all()
    for row in rows:
        normalized = _normalize_py(row.label or "")
        conn.execute(
            sa.text("UPDATE transactions SET normalized_label = :n WHERE id = :id"),
            {"n": normalized, "id": row.id},
        )


def downgrade() -> None:
    op.drop_index("ix_tx_categorized_by", table_name="transactions")
    op.drop_index("ix_tx_normalized_label", table_name="transactions")
    op.drop_column("transactions", "categorization_rule_id")
    op.drop_column("transactions", "categorized_by")
    op.drop_column("transactions", "normalized_label")

    op.drop_index("ix_rule_entity_priority", table_name="categorization_rules")
    op.drop_index("uq_rule_priority_per_scope", table_name="categorization_rules")
    op.drop_table("categorization_rules")

    for enum_name in (
        "transaction_categorization_source",
        "rule_direction",
        "rule_amount_operator",
        "rule_label_operator",
    ):
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
