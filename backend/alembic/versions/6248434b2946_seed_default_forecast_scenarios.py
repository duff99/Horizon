"""seed_default_forecast_scenarios

Crée un scénario "Principal" (is_default=true) pour chaque entité existante
qui n'en a pas encore. Idempotent grâce au `WHERE NOT EXISTS`.

Attribué au premier user admin actif (par ordre d'id) si disponible, sinon
`created_by_id` reste NULL (la colonne est nullable, ON DELETE SET NULL).

Revision ID: 6248434b2946
Revises: dc932d85a8a3
Create Date: 2026-04-22 18:39:35.015532
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6248434b2946"
down_revision: Union[str, Sequence[str], None] = "dc932d85a8a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed default forecast scenario for every existing entity."""
    op.execute(
        sa.text(
            """
            INSERT INTO forecast_scenarios
                (entity_id, name, description, is_default, created_by_id,
                 created_at, updated_at)
            SELECT e.id,
                   'Principal',
                   NULL,
                   true,
                   (SELECT id FROM users
                    WHERE role = 'admin' AND is_active = true
                    ORDER BY id LIMIT 1),
                   NOW(),
                   NOW()
            FROM entities e
            WHERE NOT EXISTS (
                SELECT 1 FROM forecast_scenarios fs
                WHERE fs.entity_id = e.id AND fs.is_default = true
            )
            """
        )
    )


def downgrade() -> None:
    """Supprime les scénarios seedés.

    Perte acceptée : si l'utilisateur a créé d'autres scénarios nommés
    "Principal" manuellement, ils seront également supprimés. Les scénarios
    custom sous un autre nom ne sont pas touchés.
    """
    op.execute(
        sa.text("DELETE FROM forecast_scenarios WHERE name = 'Principal'")
    )
