"""Plan 5b : commitments + forecast_scenarios + forecast_lines.

Revision ID: dc932d85a8a3
Revises: f7a8b9c0d1e2
Create Date: 2026-04-22 10:00:00
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "dc932d85a8a3"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    commitment_direction = sa.Enum(
        "in", "out", name="commitment_direction"
    )
    commitment_status = sa.Enum(
        "pending", "paid", "cancelled", name="commitment_status"
    )
    forecast_line_method = sa.Enum(
        "RECURRING_FIXED",
        "AVG_3M",
        "AVG_6M",
        "AVG_12M",
        "PREVIOUS_MONTH",
        "SAME_MONTH_LAST_YEAR",
        "BASED_ON_CATEGORY",
        "FORMULA",
        name="forecast_line_method",
    )

    # --- commitments ---
    op.create_table(
        "commitments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "entity_id",
            sa.Integer,
            sa.ForeignKey("entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "counterparty_id",
            sa.Integer,
            sa.ForeignKey("counterparties.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "category_id",
            sa.Integer,
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "bank_account_id",
            sa.Integer,
            sa.ForeignKey("bank_accounts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("direction", commitment_direction, nullable=False),
        sa.Column("amount_cents", sa.Integer, nullable=False),
        sa.Column("issue_date", sa.Date, nullable=False),
        sa.Column("expected_date", sa.Date, nullable=False),
        sa.Column(
            "status",
            commitment_status,
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "matched_transaction_id",
            sa.Integer,
            sa.ForeignKey("transactions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reference", sa.String(255), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "pdf_attachment_id",
            sa.Integer,
            sa.ForeignKey("imports.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_by_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
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
        ),
    )
    op.create_index(
        "ix_commitments_entity_id", "commitments", ["entity_id"]
    )
    op.create_index(
        "ix_commitments_entity_status",
        "commitments",
        ["entity_id", "status"],
    )
    op.create_index(
        "ix_commitments_expected_date", "commitments", ["expected_date"]
    )
    op.create_index(
        "ix_commitments_matched_transaction_id",
        "commitments",
        ["matched_transaction_id"],
    )

    # --- forecast_scenarios ---
    op.create_table(
        "forecast_scenarios",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "entity_id",
            sa.Integer,
            sa.ForeignKey("entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "is_default",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "created_by_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
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
        ),
    )
    op.create_index(
        "ix_forecast_scenarios_entity_id",
        "forecast_scenarios",
        ["entity_id"],
    )
    # Partial unique index: 1 scenario is_default=true max par entité (Postgres).
    op.execute(
        "CREATE UNIQUE INDEX uq_forecast_scenario_default_per_entity "
        "ON forecast_scenarios (entity_id) WHERE is_default = true"
    )

    # --- forecast_lines ---
    op.create_table(
        "forecast_lines",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "scenario_id",
            sa.Integer,
            sa.ForeignKey("forecast_scenarios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "entity_id",
            sa.Integer,
            sa.ForeignKey("entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "category_id",
            sa.Integer,
            sa.ForeignKey("categories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("method", forecast_line_method, nullable=False),
        sa.Column("amount_cents", sa.Integer, nullable=True),
        sa.Column(
            "base_category_id",
            sa.Integer,
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("ratio", sa.Numeric(5, 4), nullable=True),
        sa.Column("formula_expr", sa.Text, nullable=True),
        sa.Column("start_month", sa.Date, nullable=True),
        sa.Column("end_month", sa.Date, nullable=True),
        sa.Column(
            "updated_by_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
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
        ),
        sa.UniqueConstraint(
            "scenario_id",
            "category_id",
            name="uq_forecast_line_scenario_category",
        ),
    )
    op.create_index(
        "ix_forecast_lines_scenario_id", "forecast_lines", ["scenario_id"]
    )
    op.create_index(
        "ix_forecast_lines_entity_id", "forecast_lines", ["entity_id"]
    )
    op.create_index(
        "ix_forecast_lines_category_id", "forecast_lines", ["category_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_forecast_lines_category_id", table_name="forecast_lines")
    op.drop_index("ix_forecast_lines_entity_id", table_name="forecast_lines")
    op.drop_index("ix_forecast_lines_scenario_id", table_name="forecast_lines")
    op.drop_table("forecast_lines")
    sa.Enum(name="forecast_line_method").drop(op.get_bind(), checkfirst=True)

    op.execute("DROP INDEX IF EXISTS uq_forecast_scenario_default_per_entity")
    op.drop_index(
        "ix_forecast_scenarios_entity_id", table_name="forecast_scenarios"
    )
    op.drop_table("forecast_scenarios")

    op.drop_index(
        "ix_commitments_matched_transaction_id", table_name="commitments"
    )
    op.drop_index("ix_commitments_expected_date", table_name="commitments")
    op.drop_index("ix_commitments_entity_status", table_name="commitments")
    op.drop_index("ix_commitments_entity_id", table_name="commitments")
    op.drop_table("commitments")
    sa.Enum(name="commitment_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="commitment_direction").drop(op.get_bind(), checkfirst=True)
