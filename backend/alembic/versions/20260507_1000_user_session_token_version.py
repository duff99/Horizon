"""user.session_token_version

Revision ID: h0r1z0n50701
Revises: h0r1z0n50601
Create Date: 2026-05-07
"""
from alembic import op
import sqlalchemy as sa

revision = "h0r1z0n50701"
down_revision = "h0r1z0n50601"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "session_token_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )
    op.alter_column("users", "session_token_version", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "session_token_version")
