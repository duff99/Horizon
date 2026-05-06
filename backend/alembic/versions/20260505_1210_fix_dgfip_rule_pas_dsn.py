"""Corrige la règle système "DGFIP Impôt société" qui catégorisait à tort
toutes les transactions DGFIP en Impôt sur les sociétés (PAS-DSN, TVA, etc.),
et ajoute une règle dédiée pour le Prélèvement à la source (PAS-DSN).

Effets sur la donnée existante :
- Les 6 transactions actuellement classées "Impôt sur les sociétés" (id=34)
  via la règle 2 vont être re-routées : 5 en "Prélèvement à la source"
  (PAS-DSN), 1 en "TVA à payer/rembourser" (la règle TVA prend le relais).
- Les transactions catégorisées MANUAL ne sont PAS touchées.

Revision ID: h0r1z0n50502
Revises: h0r1z0n50501
Create Date: 2026-05-05 12:10:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "h0r1z0n50502"
down_revision = "h0r1z0n50501"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    pas_cat_id = conn.execute(
        sa.text("SELECT id FROM categories WHERE slug = 'prelevement-source'")
    ).scalar_one()

    # 1) Restreindre la règle 2 (DGFIP Impôt société) : exiger un marqueur IS
    # explicite (ACOMPTE IS, IMPOT-IS) au lieu du seul mot "DGFIP".
    conn.execute(
        sa.text(
            "UPDATE categorization_rules "
            "SET label_value = :v, name = :n "
            "WHERE id = 2 AND is_system = true"
        ),
        {"v": "ACOMPTE IS, IMPOT-IS, IS-3310", "n": "DGFIP Impôt société (IS)"},
    )

    # 2) Insérer la règle PAS-DSN si absente. Priorité 1005 pour qu'elle passe
    # avant l'ancienne règle DGFIP (1010) — défense en profondeur.
    exists = conn.execute(
        sa.text(
            "SELECT id FROM categorization_rules "
            "WHERE name = 'DGFIP Prélèvement à la source (PAS-DSN)' AND entity_id IS NULL"
        )
    ).scalar_one_or_none()
    if not exists:
        # Trouver une priorité libre dans le scope global (contrainte unique
        # uq_rule_priority_per_scope sur (COALESCE(entity_id,0), priority)).
        target_prio = 1005
        while conn.execute(
            sa.text(
                "SELECT 1 FROM categorization_rules "
                "WHERE entity_id IS NULL AND priority = :p"
            ),
            {"p": target_prio},
        ).scalar_one_or_none():
            target_prio += 1

        conn.execute(
            sa.text(
                "INSERT INTO categorization_rules "
                "(name, entity_id, priority, is_system, "
                " label_operator, label_value, direction, "
                " amount_operator, amount_value, amount_value2, "
                " counterparty_id, bank_account_id, category_id, "
                " created_by_id, created_at, updated_at) "
                "VALUES "
                "(:name, NULL, :prio, true, "
                " 'CONTAINS', :lv, 'DEBIT', "
                " NULL, NULL, NULL, "
                " NULL, NULL, :cat, "
                " NULL, NOW(), NOW())"
            ),
            {
                "name": "DGFIP Prélèvement à la source (PAS-DSN)",
                "prio": target_prio,
                "lv": "PAS-DSN, PASDSN, IMPOT-PAS",
                "cat": pas_cat_id,
            },
        )

    # 3) Recatégorisation des transactions non-MANUAL pour appliquer le fix.
    # On vide d'abord les tx catégorisées par la règle 2 (qui sont fausses)
    # ET les tx NONE, puis on relancera l'apply via l'app au prochain reload.
    # Ici on fait directement le re-routage attendu en SQL pour fiabilité.

    # 3a) Reset des tx catégorisées par la règle 2 (ancienne règle trop large)
    # qui ne contiennent PAS un marqueur IS — elles seront re-catégorisées.
    conn.execute(
        sa.text(
            "UPDATE transactions "
            "SET category_id = NULL, categorization_rule_id = NULL, "
            "    categorized_by = 'NONE' "
            "WHERE categorization_rule_id = 2 "
            "  AND categorized_by = 'RULE' "
            "  AND UPPER(COALESCE(normalized_label, label)) NOT LIKE '%ACOMPTE IS%' "
            "  AND UPPER(COALESCE(normalized_label, label)) NOT LIKE '%IMPOT-IS%' "
            "  AND UPPER(COALESCE(normalized_label, label)) NOT LIKE '%IS-3310%'"
        )
    )

    # 3b) Pour les tx NONE qui matchent les nouvelles règles (PAS-DSN, TVA),
    # on laisse l'application tourner son apply au prochain démarrage. Mais
    # pour garantir l'effet immédiat, on fait l'UPDATE SQL équivalent ici.

    pas_rule = conn.execute(
        sa.text(
            "SELECT id FROM categorization_rules "
            "WHERE name = 'DGFIP Prélèvement à la source (PAS-DSN)'"
        )
    ).scalar_one()

    # PAS-DSN
    conn.execute(
        sa.text(
            "UPDATE transactions SET "
            "  category_id = :cat, categorization_rule_id = :rid, "
            "  categorized_by = 'RULE' "
            "WHERE categorized_by = 'NONE' "
            "  AND amount < 0 "
            "  AND ("
            "    UPPER(COALESCE(normalized_label, label)) LIKE '%PAS-DSN%' OR "
            "    UPPER(COALESCE(normalized_label, label)) LIKE '%PASDSN%' OR "
            "    UPPER(COALESCE(normalized_label, label)) LIKE '%IMPOT-PAS%'"
            "  )"
        ),
        {"cat": pas_cat_id, "rid": pas_rule},
    )

    # TVA débit (rule id=3, category 33)
    conn.execute(
        sa.text(
            "UPDATE transactions SET "
            "  category_id = 33, categorization_rule_id = 3, "
            "  categorized_by = 'RULE' "
            "WHERE categorized_by = 'NONE' "
            "  AND amount < 0 "
            "  AND UPPER(COALESCE(normalized_label, label)) LIKE '%TVA%'"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()

    # Restaurer l'ancienne règle DGFIP large.
    conn.execute(
        sa.text(
            "UPDATE categorization_rules "
            "SET label_value = 'DGFIP', name = 'DGFIP Impôt société' "
            "WHERE id = 2 AND is_system = true"
        )
    )

    # Supprimer la règle PAS-DSN ; les tx pointant dessus deviennent NONE.
    conn.execute(
        sa.text(
            "UPDATE transactions SET "
            "  category_id = NULL, categorization_rule_id = NULL, "
            "  categorized_by = 'NONE' "
            "WHERE categorization_rule_id IN ("
            "  SELECT id FROM categorization_rules "
            "  WHERE name = 'DGFIP Prélèvement à la source (PAS-DSN)'"
            ")"
        )
    )
    conn.execute(
        sa.text(
            "DELETE FROM categorization_rules "
            "WHERE name = 'DGFIP Prélèvement à la source (PAS-DSN)'"
        )
    )
