"""F6 — Vérifie que normalize_label supprime les caractères problématiques
et que les label_value en DB sont toujours des versions normalisées valides.

Note sur les règles multi-valeurs (is_system=true) :
Le moteur de catégorisation split les label_value sur la virgule
(services/categorization.py l. 28 et 85) pour supporter des patterns OR.
Ces valeurs multi-patterns sont insérées via migration SQL sans passer
par le validator Pydantic. Ce fichier exempte les règles is_system=true
de la contrainte de normalisation stricte pour ne pas faux-positiver sur
les virgules légitimes.

Les règles user-defined (is_system=false) passent par le validator
_normalize_label_value du schéma Pydantic avant persistance ; elles ne
peuvent donc pas contenir de caractères non normalisés ni de virgules.
"""
from sqlalchemy import select

from app.models.categorization_rule import CategorizationRule
from app.parsers.normalization import normalize_label


def test_normalize_strips_asterisks():
    """Les astérisques sont supprimés par normalize_label."""
    assert normalize_label("FRAIS **") == "FRAIS"


def test_normalize_strips_parentheses():
    assert normalize_label("VIR (REF)") == "VIR REF"


def test_normalize_is_idempotent():
    """Appliquer normalize_label deux fois donne le même résultat."""
    v = "DGFIP IMPOTS"
    assert normalize_label(normalize_label(v)) == normalize_label(v)


def test_normalize_strips_commas():
    """Les virgules sont supprimées (remplacées par espace) par normalize_label."""
    assert normalize_label("FRAIS, AGIOS") == "FRAIS AGIOS"


def test_all_user_rule_label_values_are_normalized(db_session):
    """Chaque label_value de règle user-defined doit être identique à sa
    version normalisée.

    Ce test détecte toute règle user-defined dont la valeur n'a pas été
    normalisée à la création (régression du validator Pydantic ou d'une
    insertion directe en SQL contournant le schéma).

    Les règles is_system=true sont exemptées car elles sont insérées via
    migration SQL et peuvent contenir des virgules comme séparateurs
    multi-patterns (design intentionnel du moteur de matching).
    """
    rules = db_session.scalars(
        select(CategorizationRule).where(
            CategorizationRule.label_value.isnot(None),
            CategorizationRule.is_system.is_(False),
        )
    ).all()
    bad = [
        (r.id, r.name, r.label_value, normalize_label(r.label_value))
        for r in rules
        if r.label_value and normalize_label(r.label_value) != r.label_value
    ]
    assert bad == [], (
        f"Règles user-defined avec label_value non normalisé : {bad}. "
        "Corriger via UPDATE SQL transactionnel dans la DB."
    )


def test_system_rules_with_broken_normalization_are_documented(db_session):
    """Inventorie les règles is_system=true dont le label_value contient des
    caractères supprimés par normalize_label (hors virgules intentionnelles).

    Ce test ne FAIL pas — il sert de détecteur documenté. Les règles
    identifiées ici sont des bugs de migration à traiter via une nouvelle
    migration Alembic (pas via UPDATE SQL direct).

    Règles connues à la date du commit F6 :
      - id=103 : 'FRAIS **' (les ** sont supprimés → STARTS_WITH ne matche rien)
    """
    rules = db_session.scalars(
        select(CategorizationRule).where(
            CategorizationRule.label_value.isnot(None),
            CategorizationRule.is_system.is_(True),
        )
    ).all()

    # Pour les règles system multi-valeurs (virgule = séparateur légitime),
    # on normalise chaque pattern individuellement.
    broken = []
    for r in rules:
        if not r.label_value:
            continue
        patterns = [p.strip() for p in r.label_value.split(",") if p.strip()]
        bad_patterns = [p for p in patterns if normalize_label(p) != p]
        if bad_patterns:
            broken.append((r.id, r.name, bad_patterns))

    # Règles cassées connues et documentées (ne pas corriger sans migration).
    # Identifiées par leur nom (stable entre DB de test et de prod) car les IDs
    # peuvent différer selon l'environnement.
    #
    # Bugs identifiés lors de l'audit F6 (2026-05-07) :
    #   - 'Frais bancaires divers (Frais **)' : 'FRAIS **' → 'FRAIS'
    #     Bug migration 20260505_1510 ; STARTS_WITH 'FRAIS **' ne matche rien.
    #   - 'Anthropic / Claude.ai' : 'CLAUDE.AI' → 'CLAUDE AI'
    #     Le '.' est supprimé par normalize_label ; CONTAINS 'CLAUDE AI' serait
    #     trop large. A corriger via migration Alembic.
    known_broken_names = {
        "Frais bancaires divers (Frais **)",
        "Anthropic / Claude.ai",
    }

    unknown_broken = [(id_, name, pats) for id_, name, pats in broken
                      if name not in known_broken_names]

    assert unknown_broken == [], (
        f"Nouvelles règles system avec patterns non normalisés détectées : "
        f"{unknown_broken}. Créer une migration Alembic pour les corriger."
    )
