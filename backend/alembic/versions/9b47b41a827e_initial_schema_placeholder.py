"""initial schema — users, entities, user_entity_access, bank_accounts

Revision ID: 9b47b41a827e
Revises:
Create Date: 2026-04-16 17:48:06.167002

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9b47b41a827e"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Schema initial : utilisateurs, sociétés, liaisons, comptes bancaires."""

    # users
    user_role_enum = sa.Enum("admin", "reader", name="user_role")
    user_role_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # entities
    op.create_table(
        "entities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("legal_name", sa.String(255), nullable=False),
        sa.Column("siret", sa.String(32), nullable=True),
        sa.Column(
            "parent_entity_id",
            sa.Integer(),
            sa.ForeignKey("entities.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # user_entity_access
    op.create_table(
        "user_entity_access",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "entity_id",
            sa.Integer(),
            sa.ForeignKey("entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "entity_id", name="uq_user_entity"),
    )
    op.create_index("ix_user_entity_access_user_id", "user_entity_access", ["user_id"])
    op.create_index("ix_user_entity_access_entity_id", "user_entity_access", ["entity_id"])

    # bank_accounts
    op.create_table(
        "bank_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "entity_id",
            sa.Integer(),
            sa.ForeignKey("entities.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("iban", sa.String(34), nullable=False, unique=True),
        sa.Column("bic", sa.String(11), nullable=True),
        sa.Column("bank_name", sa.String(255), nullable=False),
        sa.Column(
            "bank_code",
            sa.String(50),
            nullable=False,
            comment="Code interne : 'delubac', 'qonto', etc.",
        ),
        sa.Column("account_number", sa.String(34), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_bank_accounts_entity_id", "bank_accounts", ["entity_id"])


def downgrade() -> None:
    """Rollback : supprime toutes les tables dans l'ordre inverse."""
    op.drop_index("ix_bank_accounts_entity_id", table_name="bank_accounts")
    op.drop_table("bank_accounts")
    op.drop_index("ix_user_entity_access_entity_id", table_name="user_entity_access")
    op.drop_index("ix_user_entity_access_user_id", table_name="user_entity_access")
    op.drop_table("user_entity_access")
    op.drop_table("entities")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    sa.Enum(name="user_role").drop(op.get_bind(), checkfirst=True)
