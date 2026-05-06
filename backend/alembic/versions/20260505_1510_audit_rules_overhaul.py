"""Refonte massive des règles de catégorisation suite à l'audit data
2026-05-05 (4 mois importés, 711 transactions).

Effets :
- Corrige les règles seed inopérantes (Virement salaire, Acompte) qui ne
  matchaient aucune transaction réelle.
- Durcit les règles à risque latent (FREE, EDF) en spécifiant les variantes
  réelles plutôt que des fragments génériques.
- Reclasse la règle "Malakoff Humanis" Prévoyance → Retraite (5 tx,
  ~7 700 €) : les libellés réels disent "Retraite Malakoff Humanis".
- Ajoute 13 règles métier basées sur les patterns observés (Cabinet
  Allegre Faure, Anthropic, Fygr, Frais ** bancaires, Swisslife, DKV,
  SCP Durand Delay, SolarFacility, Acronos, sous-traitants nominatifs,
  Steven Breuil dirigeant, Rejet Prlv).
- Reclasse manuellement deux blocs :
  * 12 transactions "Intérêts de retard rétro" mal classées en
    Commissions bancaires (MANUAL) → Produits financiers.
  * Lignes Dailly / Rem créance / BNP Paribas Factor → Affacturage / Dailly.

Revision ID: h0r1z0n50504
Revises: h0r1z0n50503
Create Date: 2026-05-05 15:10:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "h0r1z0n50504"
down_revision = "h0r1z0n50503"
branch_labels = None
depends_on = None


NEW_RULES: list[dict] = [
    # name, label_operator, label_value, direction, category_slug, priority
    {
        "name": "Cabinet Allegre Faure (expert-comptable)",
        "op": "CONTAINS",
        "lv": "CABINET ALLEGRE FAURE, ALLEGRE FAURE",
        "dir": "DEBIT",
        "cat": "honoraires-conseil",
        "prio": 1300,
    },
    {
        "name": "Anthropic / Claude.ai",
        "op": "CONTAINS",
        "lv": "ANTHROPIC, CLAUDE.AI",
        "dir": "DEBIT",
        "cat": "informatique-logiciels",
        "prio": 1310,
    },
    {
        "name": "Fygr (logiciel trésorerie)",
        "op": "CONTAINS",
        "lv": "FYGR",
        "dir": "DEBIT",
        "cat": "informatique-logiciels",
        "prio": 1320,
    },
    {
        "name": "Frais carte étranger",
        "op": "STARTS_WITH",
        "lv": "PRLV FRAIS CARTE",
        "dir": "DEBIT",
        "cat": "frais-cartes",
        "prio": 1330,
    },
    {
        "name": "Cotisation compte pro",
        "op": "STARTS_WITH",
        "lv": "PRLV OFFRE COMPTE",
        "dir": "DEBIT",
        "cat": "commissions",
        "prio": 1340,
    },
    {
        "name": "Frais bancaires divers (Frais **)",
        "op": "STARTS_WITH",
        "lv": "FRAIS **",
        "dir": "DEBIT",
        "cat": "commissions",
        "prio": 1350,
    },
    {
        "name": "Swisslife (prévoyance / assurance)",
        "op": "CONTAINS",
        "lv": "SWISSLIFE",
        "dir": "DEBIT",
        "cat": "prevoyance",
        "prio": 1360,
    },
    {
        "name": "Rejet de prélèvement",
        "op": "CONTAINS",
        "lv": "REJET PRLV, REJET DE PRLV",
        "dir": "ANY",
        "cat": "ajustements",
        "prio": 1370,
    },
    {
        "name": "DKV (carburant / péages)",
        "op": "CONTAINS",
        "lv": "DKV EURO SERVICE, DKV",
        "dir": "DEBIT",
        "cat": "deplacements-missions",
        "prio": 1380,
    },
    {
        "name": "SCP Durand Delay (huissier)",
        "op": "CONTAINS",
        "lv": "SCP DURAND DELAY, DURAND DELAY",
        "dir": "DEBIT",
        "cat": "honoraires-juridiques",
        "prio": 1390,
    },
    {
        "name": "SolarFacility (location panneaux)",
        "op": "CONTAINS",
        "lv": "SOLARFACILITY, SOLAR FACILITY",
        "dir": "DEBIT",
        "cat": "energie-eau",
        "prio": 1400,
    },
    {
        "name": "Acronos (holding / fournisseur)",
        "op": "CONTAINS",
        "lv": "ACRONOS",
        "dir": "DEBIT",
        "cat": "decaissements-fournisseurs",
        "prio": 1410,
    },
    {
        "name": "Sous-traitants nominatifs",
        "op": "CONTAINS",
        "lv": "NIZAR MOUADDEB, KAISSA BERRAHMOUNE, ABDELHAMID DJERIDI",
        "dir": "DEBIT",
        "cat": "sous-traitance-generique",
        "prio": 1420,
    },
    {
        "name": "Steven Breuil (virements dirigeant)",
        "op": "CONTAINS",
        "lv": "STEVEN BREUIL",
        "dir": "ANY",
        "cat": "depenses-personnelles",
        "prio": 1430,
    },
    {
        "name": "Acreed Consulting (intra-groupe)",
        "op": "CONTAINS",
        "lv": "ACREED CONSULTING",
        "dir": "ANY",
        "cat": "flux-intergroupe",
        "prio": 1440,
    },
    {
        "name": "Affacturage Dailly",
        "op": "CONTAINS",
        "lv": "VIR DU COMPTE DAILLY, REM CREANCE, RETENUE GARANTIE, REGLEMENT CREANCE, BNP PARIBAS FACTOR",
        "dir": "ANY",
        "cat": "affacturage-dailly",
        "prio": 1450,
    },
]


def _resolve_cat(conn, slug: str) -> int:
    res = conn.execute(
        sa.text("SELECT id FROM categories WHERE slug = :s"), {"s": slug}
    ).scalar_one_or_none()
    if res is None:
        raise RuntimeError(f"Catégorie '{slug}' introuvable")
    return int(res)


def upgrade() -> None:
    conn = op.get_bind()

    # ------------------------------------------------------------------
    # 1) Mise à jour des règles existantes
    # ------------------------------------------------------------------

    # Règle 5 : VIR SEPA SALAIRE → Salaire (CONTAINS) car les libellés
    # réels sont "VIR SEPA <Nom> Salaire <Mois>" (le nom apparaît avant
    # SALAIRE, donc STARTS_WITH ne matche jamais).
    conn.execute(
        sa.text(
            "UPDATE categorization_rules "
            "SET label_operator = 'CONTAINS', label_value = 'SALAIRE' "
            "WHERE id = 5 AND is_system = true"
        )
    )

    # Règle 6 : ACOMPTE → AVANCE SALAIRE / AVANCE SUR SALAIRE / AVANCE DE SALAIRE
    # (les libellés réels disent "Avance" pas "Acompte").
    conn.execute(
        sa.text(
            "UPDATE categorization_rules "
            "SET label_value = 'AVANCE SALAIRE, AVANCE SUR SALAIRE, AVANCE DE SALAIRE' "
            "WHERE id = 6 AND is_system = true"
        )
    )

    # Règle 8 : Malakoff = Retraite, pas Prévoyance. 5 tx mal classées.
    retraite_id = _resolve_cat(conn, "retraite")
    conn.execute(
        sa.text(
            "UPDATE categorization_rules "
            "SET name = 'Malakoff Humanis Retraite', "
            "    label_value = 'MALAKOFF HUMANIS RETRAITE, RETRAITE MALAKOFF', "
            "    category_id = :c "
            "WHERE id = 8 AND is_system = true"
        ),
        {"c": retraite_id},
    )

    # Règle 13 : EDF générique → variantes B2B uniquement.
    conn.execute(
        sa.text(
            "UPDATE categorization_rules "
            "SET label_value = 'EDF ENTREPRISE, EDF PRO, EDF COLLECTIVITES' "
            "WHERE id = 13 AND is_system = true"
        )
    )

    # Règle 18 : FREE générique (risque "FREELANCE", "FREEPIK") → variantes
    # télécom uniquement.
    conn.execute(
        sa.text(
            "UPDATE categorization_rules "
            "SET label_value = 'FREE SAS, FREE PRO, FREE MOBILE, FREE TELECOM' "
            "WHERE id = 18 AND is_system = true"
        )
    )

    # ------------------------------------------------------------------
    # 2) Insertion des nouvelles règles (idempotent par nom).
    # ------------------------------------------------------------------
    for rule in NEW_RULES:
        cat_id = _resolve_cat(conn, rule["cat"])
        already = conn.execute(
            sa.text(
                "SELECT id FROM categorization_rules "
                "WHERE name = :n AND entity_id IS NULL"
            ),
            {"n": rule["name"]},
        ).scalar_one_or_none()
        if already:
            continue

        # Trouver une priorité libre (la souhaitée puis incrémente).
        target = rule["prio"]
        while conn.execute(
            sa.text(
                "SELECT 1 FROM categorization_rules "
                "WHERE entity_id IS NULL AND priority = :p"
            ),
            {"p": target},
        ).scalar_one_or_none():
            target += 1

        conn.execute(
            sa.text(
                "INSERT INTO categorization_rules "
                "(name, entity_id, priority, is_system, "
                " label_operator, label_value, direction, "
                " amount_operator, amount_value, amount_value2, "
                " counterparty_id, bank_account_id, category_id, "
                " created_by_id, created_at, updated_at) "
                "VALUES (:n, NULL, :p, true, "
                " :op, :lv, :dir, "
                " NULL, NULL, NULL, NULL, NULL, :c, "
                " NULL, NOW(), NOW())"
            ),
            {
                "n": rule["name"],
                "p": target,
                "op": rule["op"],
                "lv": rule["lv"],
                "dir": rule["dir"],
                "c": cat_id,
            },
        )

    # ------------------------------------------------------------------
    # 3) Recatégorisation : reset toutes les transactions RULE (les MANUAL
    # ne sont jamais touchées) puis re-routage SQL pour matcher les
    # nouvelles règles. Les RULE qui ne matchent plus rien deviennent NONE
    # et seront recapturées par l'apply au prochain démarrage.
    # ------------------------------------------------------------------

    # 3a) Reset RULE → NONE pour réévaluation propre.
    conn.execute(
        sa.text(
            "UPDATE transactions SET "
            "  category_id = NULL, categorization_rule_id = NULL, "
            "  categorized_by = 'NONE' "
            "WHERE categorized_by = 'RULE'"
        )
    )

    # 3b) Re-routage SQL des nouvelles règles + règles modifiées. On
    # applique chaque règle dans l'ordre de priorité ; la première qui
    # matche gagne (NONE only, on ne touche pas MANUAL).
    rules_in_order = conn.execute(
        sa.text(
            "SELECT id, label_operator, label_value, direction, category_id "
            "FROM categorization_rules "
            "WHERE entity_id IS NULL AND label_operator IS NOT NULL "
            "  AND label_value IS NOT NULL "
            "ORDER BY priority ASC"
        )
    ).fetchall()

    for rid, op_, lv, direction, cat in rules_in_order:
        patterns = [p.strip() for p in lv.split(",") if p.strip()]
        if not patterns:
            continue
        like_clauses: list[str] = []
        params: dict = {"rid": rid, "cat": cat}
        for i, pat in enumerate(patterns):
            key = f"p{i}"
            if op_ == "CONTAINS":
                like_clauses.append(
                    f"UPPER(COALESCE(normalized_label, label)) LIKE :{key}"
                )
                params[key] = f"%{pat.upper()}%"
            elif op_ == "STARTS_WITH":
                like_clauses.append(
                    f"UPPER(COALESCE(normalized_label, label)) LIKE :{key}"
                )
                params[key] = f"{pat.upper()}%"
            elif op_ == "ENDS_WITH":
                like_clauses.append(
                    f"UPPER(COALESCE(normalized_label, label)) LIKE :{key}"
                )
                params[key] = f"%{pat.upper()}"
            elif op_ == "EQUALS":
                like_clauses.append(
                    f"UPPER(COALESCE(normalized_label, label)) = :{key}"
                )
                params[key] = pat.upper()
        if not like_clauses:
            continue

        dir_clause = ""
        if direction == "CREDIT":
            dir_clause = " AND amount > 0"
        elif direction == "DEBIT":
            dir_clause = " AND amount < 0"

        sql = (
            "UPDATE transactions SET "
            "  category_id = :cat, categorization_rule_id = :rid, "
            "  categorized_by = 'RULE' "
            "WHERE categorized_by = 'NONE'"
            f"{dir_clause}"
            f"  AND ({' OR '.join(like_clauses)})"
        )
        conn.execute(sa.text(sql), params)

    # ------------------------------------------------------------------
    # 4) Reclassement des MANUAL erronés.
    # ------------------------------------------------------------------

    # 4a) Intérêts de retard rétro : tx MANUAL dans cat "Commissions bancaires"
    # mais en réalité produits financiers (montants positifs sur libellés
    # "Intérêts de retard").
    pf_id = _resolve_cat(conn, "produits-financiers")
    conn.execute(
        sa.text(
            "UPDATE transactions SET category_id = :pf "
            "WHERE categorized_by = 'MANUAL' "
            "  AND amount > 0 "
            "  AND UPPER(COALESCE(normalized_label, label)) LIKE '%INTERETS DE RETARD%'"
        ),
        {"pf": pf_id},
    )

    # 4b) Affacturage Dailly : tx MANUAL en "Non identifiés" qui contiennent
    # les patterns Dailly/créance.
    aff_id = _resolve_cat(conn, "affacturage-dailly")
    conn.execute(
        sa.text(
            "UPDATE transactions SET category_id = :aff "
            "WHERE categorized_by = 'MANUAL' "
            "  AND ("
            "    UPPER(COALESCE(normalized_label, label)) LIKE '%DAILLY%' OR "
            "    UPPER(COALESCE(normalized_label, label)) LIKE '%REM CREANCE%' OR "
            "    UPPER(COALESCE(normalized_label, label)) LIKE '%REGLEMENT CREANCE%' OR "
            "    UPPER(COALESCE(normalized_label, label)) LIKE '%RETENUE GARANTIE%' OR "
            "    UPPER(COALESCE(normalized_label, label)) LIKE '%BNP PARIBAS FACTOR%'"
            "  )"
        ),
        {"aff": aff_id},
    )


def downgrade() -> None:
    """Downgrade ne tente PAS de restaurer les catégorisations MANUAL
    (impossible sans snapshot). Restaure uniquement les règles modifiées
    et supprime les nouvelles règles (les transactions associées passent
    en NONE et seront recapturées au prochain apply).
    """
    conn = op.get_bind()

    # Reset RULE pour reprise propre.
    conn.execute(
        sa.text(
            "UPDATE transactions SET "
            "  category_id = NULL, categorization_rule_id = NULL, "
            "  categorized_by = 'NONE' "
            "WHERE categorized_by = 'RULE'"
        )
    )

    # Restaurer règles seed.
    conn.execute(
        sa.text(
            "UPDATE categorization_rules SET "
            "  label_operator = 'STARTS_WITH', label_value = 'VIR SEPA SALAIRE' "
            "WHERE id = 5"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE categorization_rules SET label_value = 'ACOMPTE' WHERE id = 6"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE categorization_rules SET "
            "  name = 'Prévoyance Malakoff', label_value = 'MALAKOFF', "
            "  category_id = (SELECT id FROM categories WHERE slug = 'prevoyance') "
            "WHERE id = 8"
        )
    )
    conn.execute(
        sa.text("UPDATE categorization_rules SET label_value = 'EDF' WHERE id = 13")
    )
    conn.execute(
        sa.text("UPDATE categorization_rules SET label_value = 'FREE' WHERE id = 18")
    )

    # Supprimer les règles nouvelles.
    names = [r["name"] for r in NEW_RULES]
    conn.execute(
        sa.text(
            "DELETE FROM categorization_rules WHERE name = ANY(:names) AND entity_id IS NULL"
        ),
        {"names": names},
    )
