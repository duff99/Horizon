"""plan1: transactions imports categories counterparties

Revision ID: a1b2c3d4e5f6
Revises: 9b47b41a827e
Create Date: 2026-04-17 09:43:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "9b47b41a827e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


counterparty_status_enum = postgresql.ENUM(
    "pending", "active", "ignored",
    name="counterparty_status",
    create_type=False,
)
import_status_enum = postgresql.ENUM(
    "pending", "completed", "failed",
    name="import_status",
    create_type=False,
)


def upgrade() -> None:
    # 1. Enums créés explicitement avant les tables qui les utilisent
    counterparty_status_enum.create(op.get_bind(), checkfirst=True)
    import_status_enum.create(op.get_bind(), checkfirst=True)

    # 2. categories
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("color", sa.String(9), nullable=True),
        sa.Column("parent_category_id", sa.Integer(),
                  sa.ForeignKey("categories.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.UniqueConstraint("slug", name="uq_categories_slug"),
    )

    # 3. counterparties
    op.create_table(
        "counterparties",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(),
                  sa.ForeignKey("entities.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("normalized_name", sa.String(200), nullable=False),
        sa.Column("status", counterparty_status_enum, nullable=False,
                  server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.UniqueConstraint("entity_id", "normalized_name",
                            name="uq_counterparties_entity_normalized"),
    )
    op.create_index("ix_counterparties_entity", "counterparties", ["entity_id"])
    op.create_index("ix_counterparties_normalized", "counterparties",
                    ["normalized_name"])

    # 4. imports
    op.create_table(
        "imports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bank_account_id", sa.Integer(),
                  sa.ForeignKey("bank_accounts.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("uploaded_by_id", sa.Integer(),
                  sa.ForeignKey("users.id", ondelete="RESTRICT"),
                  nullable=True),
        sa.Column("filename", sa.String(255), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("file_sha256", sa.String(64), nullable=True),
        sa.Column("bank_code", sa.String(32), nullable=False),
        sa.Column("status", import_status_enum, nullable=False,
                  server_default="pending"),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("opening_balance", sa.Numeric(14, 2), nullable=True),
        sa.Column("closing_balance", sa.Numeric(14, 2), nullable=True),
        sa.Column("imported_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicates_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("counterparties_pending_created", sa.Integer(), nullable=False,
                  server_default="0"),
        sa.Column("override_duplicates", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("audit", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_imports_bank_account", "imports", ["bank_account_id"])
    op.create_index("ix_imports_file_sha256", "imports", ["file_sha256"])

    # 5. transactions
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bank_account_id", sa.Integer(),
                  sa.ForeignKey("bank_accounts.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("import_id", sa.Integer(),
                  sa.ForeignKey("imports.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("parent_transaction_id", sa.Integer(),
                  sa.ForeignKey("transactions.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("category_id", sa.Integer(),
                  sa.ForeignKey("categories.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("counterparty_id", sa.Integer(),
                  sa.ForeignKey("counterparties.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("counter_entity_id", sa.Integer(),
                  sa.ForeignKey("entities.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("operation_date", sa.Date(), nullable=False),
        sa.Column("value_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("label", sa.String(500), nullable=False),
        sa.Column("raw_label", sa.String(500), nullable=False),
        sa.Column("dedup_key", sa.String(64), nullable=False),
        sa.Column("statement_row_index", sa.Integer(), nullable=False),
        sa.Column("is_aggregation_parent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_intercompany", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_tx_operation_date", "transactions", ["operation_date"])
    op.create_index("ix_tx_bank_account_date", "transactions",
                    ["bank_account_id", "operation_date"])
    op.create_index("ix_tx_category", "transactions", ["category_id"])
    op.create_index("ix_tx_counterparty", "transactions", ["counterparty_id"])
    op.create_index("uq_tx_dedup_key", "transactions", ["dedup_key"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_tx_dedup_key", table_name="transactions")
    op.drop_index("ix_tx_counterparty", table_name="transactions")
    op.drop_index("ix_tx_category", table_name="transactions")
    op.drop_index("ix_tx_bank_account_date", table_name="transactions")
    op.drop_index("ix_tx_operation_date", table_name="transactions")
    op.drop_table("transactions")
    op.drop_index("ix_imports_file_sha256", table_name="imports")
    op.drop_index("ix_imports_bank_account", table_name="imports")
    op.drop_table("imports")
    op.drop_index("ix_counterparties_normalized", table_name="counterparties")
    op.drop_index("ix_counterparties_entity", table_name="counterparties")
    op.drop_table("counterparties")
    op.drop_table("categories")
    import_status_enum.drop(op.get_bind(), checkfirst=True)
    counterparty_status_enum.drop(op.get_bind(), checkfirst=True)
