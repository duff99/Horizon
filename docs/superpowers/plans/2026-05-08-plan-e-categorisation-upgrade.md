# Plan E — Catégorisation upgrade — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** Monter le taux de catégorisation de 74,6 % à 90 % ou plus. Dix items (E1–E10) couvrant l'ajout de règles génériques manquantes, l'idempotence SHA-256 sur les imports, l'aperçu live debounced dans RuleForm, l'auto-suggestion de règle après catégorisations manuelles répétées, la page admin pour les erreurs client, le bulk-catégorize sur filtre complet, le toggle SEPA, les filtres montant + persistance URL, le hit-count par règle, et l'affichage du window_month dans AnalysePage.

**Architecture :**
- Backend (Python/FastAPI/SQLAlchemy 2.x) : 1 migration seeding (E1), 1 migration idempotence imports (E2), 1 nouveau schéma `BulkCategorizeFilteredRequest` (E6), 1 nouveau endpoint `GET /api/rules/auto-suggest` (E4), 1 migration `acknowledged_at` sur `client_errors` + nouveau endpoint `PATCH /api/admin/client-errors/{id}/acknowledge` (E5), extensions `TransactionFilter` + `list_transactions` (E7, E8), endpoint `GET /api/rules` enrichi d'un COUNT agrégé par join (E9).
- Frontend (React 18 / TS / react-query / Tailwind) : debounce dans `RuleForm.tsx` (E3), toaster auto-suggest dans `TransactionsPage.tsx` (E4), nouvelle page `AdminClientErrorsPage.tsx` + route + sidebar (E5), checkbox "Sélectionner tous les résultats" + call `bulk-categorize-filtered` (E6), toggle SEPA dans `TransactionsPage.tsx` + `TransactionFilters.tsx` (E7), inputs `amount_min`/`amount_max` + `useSearchParams` (E8), colonne Hits dans `SortableRulesTable.tsx` (E9), bandeau `window_month` dans `TopMoversCard.tsx` (E10).
- Tests : pytest dans le container backend ; Vitest pour le frontend.
- Documentation d'impact (règle CLAUDE.md) : E3, E5, E6, E7, E8, E9 sont visibles utilisateur → mises à jour `documentation.ts` + tooltips. E1 : seeding documenté. E4 : toaster, bandeau + doc. E10 : polish pur.

**Tech Stack :** FastAPI, SQLAlchemy 2.x, Postgres, Alembic, React 18, react-query 5, react-router-dom 6, TypeScript, Tailwind, pytest, Vitest.

---

## File Structure

### Création

- `backend/alembic/versions/20260507_2000_e1_seed_missing_rules.py` — migration idempotente seeding des nouvelles règles (INSERT … ON CONFLICT DO NOTHING sur `categorization_rules` par `name` et `priority`). Révision : `h0r1z0ne0100`.
- `backend/alembic/versions/20260507_2010_e2_import_sha256_unique.py` — ajoute contrainte `UNIQUE (bank_account_id, file_sha256)` sur `import_records` via `CREATE UNIQUE INDEX CONCURRENTLY` (idempotent via `IF NOT EXISTS`). Révision : `h0r1z0ne0200`.
- `backend/alembic/versions/20260507_2020_e5_client_error_acknowledged.py` — ajoute colonne `acknowledged_at TIMESTAMPTZ NULL` sur `client_errors`. Révision : `h0r1z0ne0500`.
- `backend/tests/test_e1_seed_rules.py` — vérifie que les règles seeding existent en DB après migration et ne sont pas dupliquées si la migration est rejouée.
- `backend/tests/test_e2_import_idempotence.py` — upload simulé 2× → même `import_id`.
- `backend/tests/test_e4_auto_suggest.py` — endpoint `GET /api/rules/auto-suggest` retourne des suggestions quand l'audit log contient ≥ 3 catégorisations MANUAL identiques.
- `backend/tests/test_e5_client_errors_admin.py` — liste, filtres, acquittement.
- `backend/tests/test_e6_bulk_categorize_filtered.py` — `POST /api/transactions/bulk-categorize-filtered` catégorise uniquement les transactions de l'entité accessible.
- `backend/tests/test_e8_transaction_filters.py` — filtres `amount_min`/`amount_max` et `include_sepa_children`.
- `backend/tests/test_e9_rules_hit_count.py` — `GET /api/rules` retourne un champ `hit_count` par règle calculé via COUNT.
- `frontend/src/pages/AdminClientErrorsPage.tsx` — page listing des erreurs client avec filtres, badge acquitté, action "Marquer acquitté".
- `frontend/src/api/clientErrors.ts` — `fetchClientErrors`, `acknowledgeClientError`, hook `useClientErrors`.

### Modification

- `backend/app/api/imports.py` — check SHA-256 avant `import_pdf_bytes`, retourne `200 OK` si doublon.
- `backend/app/api/admin_client_errors.py` — ajout endpoint `PATCH /{id}/acknowledge`.
- `backend/app/api/transactions.py` — ajout filtres `amount_min`/`amount_max` et `include_sepa_children` dans `list_transactions` ; ajout endpoint `POST /bulk-categorize-filtered`.
- `backend/app/api/rules.py` — ajout endpoint `GET /auto-suggest` ; enrichissement `GET /` avec `hit_count` via subquery COUNT.
- `backend/app/schemas/transaction.py` — ajout `amount_min: Decimal | None`, `amount_max: Decimal | None`, `include_sepa_children: bool = False` dans `TransactionFilter`.
- `backend/app/schemas/categorization_rule.py` — ajout `BulkCategorizeFilteredRequest` (champs miroirs de `TransactionFilter` + `category_id`) ; ajout `hit_count: int = 0` dans `RuleRead`.
- `backend/app/models/client_error.py` — ajout colonne `acknowledged_at`.
- `backend/app/schemas/client_error.py` — ajout `acknowledged_at: datetime | None` dans `ClientErrorRead`; ajout `ClientErrorAcknowledgeResponse`.
- `frontend/src/components/RuleForm.tsx` — debounce 450 ms sur les champs de filtre ; déclenche `previewRule` automatiquement.
- `frontend/src/components/SortableRulesTable.tsx` — ajout colonne Hits entre Conditions et Catégorie ; tri par `hit_count` desc disponible via prop.
- `frontend/src/pages/RulesPage.tsx` — passe `hit_count` à `SortableRulesTable`; état tri.
- `frontend/src/pages/TransactionsPage.tsx` — toggle SEPA, toaster auto-suggest, checkbox "Sélectionner tous les X résultats", `useSearchParams` pour persistance URL.
- `frontend/src/components/TransactionFilters.tsx` — inputs `Montant min` / `Montant max`, toggle "Afficher les virements SEPA détaillés".
- `frontend/src/api/rules.ts` — ajout `fetchAutoSuggest`, hook `useAutoSuggest`; `RuleRead` enrichi de `hit_count`.
- `frontend/src/api/transactions.ts` — ajout `bulkCategorizeFiltered`; hook `useBulkCategorizeFiltered`.
- `frontend/src/types/analysis.ts` — ajout `window_month?: string | null` dans `TopMoversResponse`.
- `frontend/src/components/analyse/TopMoversCard.tsx` — affiche le `window_month` dans le sous-titre.
- `frontend/src/router.tsx` — route `/administration/erreurs-client` wrappée dans `<AdminRoute>`.
- `frontend/src/components/Sidebar.tsx` — entrée "Erreurs client" dans le groupe Administration.
- `frontend/src/content/documentation.ts` — sections `regles` (E3, E9), `transactions` (E6, E7, E8), `admin` (E5), `admin-client-errors` (nouvelle section E5), `auto-suggest` (E4).

---

## Conventions de l'app à respecter

(Rappel pour chaque subagent — copier-coller en briefing.)

- **Tests dans le container backend uniquement.** `docker exec horizon-backend-1 pytest -x backend/tests/test_eX_xxx.py -v`.
- **Cookie session en test** : `BACKEND_COOKIE_SECURE=false` est câblé dans conftest, ne pas y toucher.
- **Migrations** : `docker cp backend/alembic/versions/<file> horizon-backend-1:/app/alembic/versions/ && docker exec horizon-backend-1 alembic upgrade head`.
- **Révisions** : chaîne E1 `h0r1z0ne0100` → E2 `h0r1z0ne0200` → E5 `h0r1z0ne0500`. `down_revision` de E1 = `h0r1z0nf0600` (dernier head Plan F). Chaque migration suivante pointe la précédente.
- **Commit messages** : français, sobre, sans emoji, format `type(scope): message`. Co-author Claude requis.
- **Doc d'impact (règle CLAUDE.md)** : tout item avec action UI à effet (E3, E4, E5, E6, E7, E8, E9) doit livrer : bandeau si concept nouveau, tooltip `<HelpTooltip>`, section `FeatureDoc` dans `documentation.ts`.
- **Pas d'emoji**, pas de `sed -i` sur DB, pas de `cat .env`.

---

## Vérifications préalables — Résultats d'exploration

### 1. Colonne Hits dans RulesPage

```bash
grep -n "hit_count\|hits" frontend/src/pages/RulesPage.tsx
```

Résultat : **aucun match.** La colonne Hits n'existe pas dans `RulesPage.tsx` ni dans `SortableRulesTable.tsx`. Il n'y a pas non plus de champ `hit_count` dans le modèle `CategorizationRule`. La valeur sera calculée en live via un COUNT sur `transactions.categorization_rule_id GROUP BY categorization_rule_id`, jointuré dans `GET /api/rules`. Calcul live retenu car la table transactions est estimée < 50 000 lignes en prod (taille Horizon à ce stade). Aucune migration de schéma n'est nécessaire pour E9.

### 2. Endpoint d'acquittement client_errors

```bash
grep -rn "acknowledged\|acquitt" backend/app/api/admin_client_errors.py
```

Résultat : **aucun match.** Le modèle `ClientError` n'a pas de colonne `acknowledged_at`. Il faut la migration E5 + le PATCH endpoint. Le schéma `ClientErrorRead` ne contient pas non plus ce champ — il faut l'étendre.

### 3. Signature de POST /api/transactions/bulk-categorize

`BulkCategorizeRequest` (`backend/app/schemas/categorization_rule.py:165`) accepte `transaction_ids: list[int]` + `category_id: int`. Il n'accepte pas de `filter` object. L'endpoint existant `POST /api/transactions/bulk-categorize` est conservé tel quel pour éviter tout breaking change. Un nouveau endpoint `POST /api/transactions/bulk-categorize-filtered` sera créé avec `BulkCategorizeFilteredRequest` (miroir des critères de `TransactionFilter` + `category_id`). Le backend reconstruit la même query SQL que `list_transactions` pour appliquer les filtres, sans limite de pagination.

### 4. URL persistence sur TransactionsPage

```bash
grep -n "useSearchParams\|searchParams" frontend/src/pages/TransactionsPage.tsx
```

Résultat : **aucun match.** Confirmé : état `filters` géré en `useState` local uniquement, non synchronisé avec l'URL. E8 migrera ce state vers `useSearchParams` de react-router-dom 6.

### 5. window_month dans TopMoversResponse

`backend/app/schemas/analysis.py:111` : `window_month: str | None = None` est présent dans le schéma backend. `frontend/src/types/analysis.ts:39` : `TopMoversResponse` ne déclare pas `window_month`. Le frontend ignore donc silencieusement la valeur. E10 corrige l'interface TS et affiche la valeur dans `TopMoversCard.tsx`.

### 6. Head migration actuelle

`h0r1z0nf0600` (`20260508_1200_fix_broken_system_rules.py`). Toutes les migrations E1+ chaîneront depuis ce head.

### 7. Règles à 0 hit (E1 — matériau brut)

La requête de vérification préalable **obligatoire** à exécuter avant d'implémenter E1 :

```bash
docker exec horizon-backend-1 python -c "
from app.db import get_session_factory
from app.models.transaction import Transaction
from sqlalchemy import select, func
Session = get_session_factory()
with Session() as s:
    rows = s.execute(
        select(Transaction.normalized_label, func.count(Transaction.id))
        .where(
            Transaction.category_id.is_(None),
            Transaction.parent_transaction_id.is_(None)
        )
        .group_by(Transaction.normalized_label)
        .order_by(func.count(Transaction.id).desc())
        .limit(50)
    ).all()
    [print(f'{r[1]:>3} | {r[0]}') for r in rows]
"
```

Les règles E1 proposées ci-dessous sont dérivées des patterns attendus d'après l'audit master et les familles identifiées. Elles devront être validées contre la sortie prod de la requête ci-dessus avant commit. Si un label_value diffère de la forme normalisée, ajuster dans la migration.

**Règles nouvelles proposées pour E1 (minimum 10) :**

| Priorité | Nom | label_operator | label_value | direction | category cible |
|---|---|---|---|---|---|
| 4010 | Paiement carte (générique) | STARTS_WITH | CARTE | DEBIT | Achats par carte |
| 4011 | Paiement CB X% | CONTAINS | CB X | DEBIT | Achats par carte |
| 4020 | Prélèvement Agicap | CONTAINS | AGICAP | ANY | Logiciels & SaaS |
| 4030 | Prime salariale | CONTAINS | PRIME | DEBIT | Rémunérations |
| 4031 | Indemnité kilométrique | CONTAINS | INDEMNITE KILOMETRIQUE | DEBIT | Notes de frais |
| 4032 | Indemnité kilométrique (abrév.) | CONTAINS | IK | DEBIT | Notes de frais |
| 4033 | Solde de tout compte | CONTAINS | SOLDE DE TOUT COMPTE | DEBIT | Rémunérations |
| 4034 | Acompte salarié | CONTAINS | ACOMPTE | DEBIT | Rémunérations |
| 4040 | Remboursement note de frais | CONTAINS | NOTE DE FRAIS | DEBIT | Notes de frais |
| 4050 | Cotisation CCI / chambre de commerce | CONTAINS | COTISATION CCI | DEBIT | Cotisations professionnelles |
| 4060 | Abonnement téléphonique | CONTAINS | ABONNEMENT TEL | DEBIT | Télécom |
| 4061 | SFR / Bouygues / Orange / Free | CONTAINS | SFR | DEBIT | Télécom |

Note : les règles carte (4010, 4011) utilisent un libellé split-virgule si nécessaire (`CARTE X, CB X`). La catégorie "Achats par carte" doit exister dans `categories` — vérifier son `id` avant la migration. Si elle n'existe pas, créer d'abord une sous-catégorie via la page admin avant d'exécuter la migration. Idem pour "Logiciels & SaaS", "Notes de frais", "Cotisations professionnelles", "Télécom" — confirmer les ids en prod.

---

## Task E1 — Règles génériques manquantes

**Files :**
- Create : `backend/alembic/versions/20260507_2000_e1_seed_missing_rules.py`
- Create : `backend/tests/test_e1_seed_rules.py`

**Pourquoi :** 25,4 % des transactions ne sont pas catégorisées. L'audit identifie les familles Carte, Agicap, Primes/IK/STC, Frais bancaires (déjà corrigé en F6) comme causes principales. Ajouter 10–12 règles système génériques couvre les patterns les plus fréquents sans configuration utilisateur.

**Steps :**

- [ ] **Step 1 : Relever les top 50 normalized_label non catégorisés en prod**

```bash
docker exec horizon-backend-1 python -c "
from app.db import get_session_factory
from app.models.transaction import Transaction
from sqlalchemy import select, func
Session = get_session_factory()
with Session() as s:
    rows = s.execute(
        select(Transaction.normalized_label, func.count(Transaction.id))
        .where(
            Transaction.category_id.is_(None),
            Transaction.parent_transaction_id.is_(None)
        )
        .group_by(Transaction.normalized_label)
        .order_by(func.count(Transaction.id).desc())
        .limit(50)
    ).all()
    [print(f'{r[1]:>3} | {r[0]}') for r in rows]
"
```

Coller la sortie dans ce plan en commentaire de PR. Ajuster les `label_value` dans la migration si la forme normalisée diffère des valeurs du tableau ci-dessus.

- [ ] **Step 2 : Récupérer les ids de catégories cibles**

```bash
docker exec horizon-backend-1 python -c "
from app.db import get_session_factory
from app.models.category import Category
from sqlalchemy import select
Session = get_session_factory()
with Session() as s:
    rows = s.execute(select(Category.id, Category.name)).all()
    [print(f'{r[0]:>3} | {r[1]}') for r in sorted(rows, key=lambda x: x[1])]
"
```

Relever les ids pour : "Achats par carte", "Logiciels & SaaS", "Rémunérations", "Notes de frais", "Cotisations professionnelles", "Télécom". Substituer les placeholders `{CAT_ID_*}` dans la migration.

- [ ] **Step 3 : Test qui échoue**

Créer `backend/tests/test_e1_seed_rules.py` :

```python
"""E1 — Vérifie que les règles génériques sont présentes après migration."""
import pytest
from sqlalchemy import select
from app.models.categorization_rule import CategorizationRule

EXPECTED_NAMES = [
    "Paiement carte (générique)",
    "Prélèvement Agicap",
    "Prime salariale",
    "Indemnité kilométrique",
    "Solde de tout compte",
]

def test_e1_rules_exist(db_session):
    for name in EXPECTED_NAMES:
        rule = db_session.execute(
            select(CategorizationRule).where(CategorizationRule.name == name)
        ).scalar_one_or_none()
        assert rule is not None, f"Règle manquante : {name!r}"
        assert rule.is_system is True

def test_e1_migration_idempotent(db_session):
    # Rejouer un INSERT ON CONFLICT DO NOTHING sur une règle existante ne doit pas créer de doublon.
    from sqlalchemy import text
    count_before = db_session.execute(
        select(CategorizationRule).where(CategorizationRule.name == "Paiement carte (générique)")
    ).scalars().all()
    db_session.execute(
        text("""
            INSERT INTO categorization_rules
                (name, priority, is_system, label_operator, label_value, direction, category_id)
            VALUES
                ('Paiement carte (générique)', 4010, true, 'STARTS_WITH', 'CARTE', 'DEBIT', :cat_id)
            ON CONFLICT DO NOTHING
        """),
        {"cat_id": count_before[0].category_id},
    )
    count_after = db_session.execute(
        select(CategorizationRule).where(CategorizationRule.name == "Paiement carte (générique)")
    ).scalars().all()
    assert len(count_before) == len(count_after)
```

Lancer :
```bash
docker exec horizon-backend-1 pytest backend/tests/test_e1_seed_rules.py -v
# Attendu : FAILED (règles absentes)
```

- [ ] **Step 4 : Migration seeding**

Créer `backend/alembic/versions/20260507_2000_e1_seed_missing_rules.py` :

```python
"""E1 — Seeding règles génériques manquantes.

Revision ID: h0r1z0ne0100
Revises: h0r1z0nf0600
Create Date: 2026-05-07 20:00:00

Ajoute 10 règles système couvrant les familles Carte, Agicap, Primes/IK/STC,
Notes de frais, Télécom, Cotisations. Idempotent : ON CONFLICT DO NOTHING.

AVANT D'APPLIQUER : vérifier les ids de catégories via :
  SELECT id, name FROM categories ORDER BY name;
et substituer les valeurs {CAT_ID_*} ci-dessous.
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "h0r1z0ne0100"
down_revision = "h0r1z0nf0600"
branch_labels = None
depends_on = None

# Substituer avant application :
CAT_CARTE = 0          # "Achats par carte"
CAT_SAAS = 0           # "Logiciels & SaaS"
CAT_REMUN = 0          # "Rémunérations" ou "Salaires"
CAT_NDF = 0            # "Notes de frais"
CAT_COTIS = 0          # "Cotisations professionnelles"
CAT_TELCO = 0          # "Télécom"

RULES = [
    # (name, priority, label_operator, label_value, direction, category_id)
    ("Paiement carte (générique)",        4010, "STARTS_WITH", "CARTE",                       "DEBIT", CAT_CARTE),
    ("Paiement CB X%",                    4011, "CONTAINS",    "CB X",                         "DEBIT", CAT_CARTE),
    ("Prélèvement Agicap",                4020, "CONTAINS",    "AGICAP",                       "ANY",   CAT_SAAS),
    ("Prime salariale",                   4030, "CONTAINS",    "PRIME",                        "DEBIT", CAT_REMUN),
    ("Indemnité kilométrique (IK)",        4031, "CONTAINS",    "INDEMNITE KILOMETRIQUE",       "DEBIT", CAT_NDF),
    ("Indemnité kilométrique (abrév.)",    4032, "CONTAINS",    "IK",                           "DEBIT", CAT_NDF),
    ("Solde de tout compte",              4033, "CONTAINS",    "SOLDE DE TOUT COMPTE",         "DEBIT", CAT_REMUN),
    ("Acompte salarié",                   4034, "CONTAINS",    "ACOMPTE",                      "DEBIT", CAT_REMUN),
    ("Note de frais (remboursement)",     4040, "CONTAINS",    "NOTE DE FRAIS",                "DEBIT", CAT_NDF),
    ("Cotisation CCI",                    4050, "CONTAINS",    "COTISATION CCI",               "DEBIT", CAT_COTIS),
    ("Abonnement SFR",                    4061, "CONTAINS",    "SFR",                          "DEBIT", CAT_TELCO),
    ("Abonnement télécom (générique)",    4062, "CONTAINS",    "ABONNEMENT TEL",               "DEBIT", CAT_TELCO),
]


def upgrade() -> None:
    bind = op.get_bind()
    for (name, priority, lop, lval, direction, cat_id) in RULES:
        bind.execute(
            sa.text("""
                INSERT INTO categorization_rules
                    (name, priority, is_system, label_operator, label_value,
                     direction, category_id, created_at, updated_at)
                VALUES
                    (:name, :priority, true, :lop, :lval,
                     :direction, :cat_id, NOW(), NOW())
                ON CONFLICT DO NOTHING
            """),
            {
                "name": name, "priority": priority, "lop": lop,
                "lval": lval, "direction": direction, "cat_id": cat_id,
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    names = [r[0] for r in RULES]
    bind.execute(
        sa.text("DELETE FROM categorization_rules WHERE name = ANY(:names) AND is_system = true"),
        {"names": names},
    )
```

Copier et appliquer :
```bash
docker cp backend/alembic/versions/20260507_2000_e1_seed_missing_rules.py \
    horizon-backend-1:/app/alembic/versions/
docker exec horizon-backend-1 alembic upgrade head
```

- [ ] **Step 5 : Test vert**

```bash
docker exec horizon-backend-1 pytest backend/tests/test_e1_seed_rules.py -v
# Attendu : 2 passed
```

- [ ] **Step 6 : Vérification du taux de couverture post-migration**

```bash
docker exec horizon-backend-1 python -c "
from app.db import get_session_factory
from app.models.transaction import Transaction
from sqlalchemy import select, func
Session = get_session_factory()
with Session() as s:
    total = s.execute(select(func.count(Transaction.id)).where(Transaction.parent_transaction_id.is_(None))).scalar()
    uncat = s.execute(select(func.count(Transaction.id)).where(Transaction.category_id.is_(None), Transaction.parent_transaction_id.is_(None))).scalar()
    print(f'Total: {total}, Non catégorisées: {uncat}, Taux: {100*(total-uncat)/total:.1f}%')
"
```

Documenter le taux dans la PR.

- [ ] **Step 7 : Commit**

```
feat(rules): E1 — seeding 12 règles système génériques (carte, Agicap, primes/IK/STC, télécom, cotisations)

Ajoute 12 règles système couvrant les familles non couvertes identifiées
dans l'audit de couverture. Migration idempotente : ON CONFLICT DO NOTHING.
Taux de couverture attendu : +~8 pts (depuis 74,6 %).

Co-authored-by: Claude <noreply@anthropic.com>
```

---

## Task E2 — Idempotence upload SHA-256

**Files :**
- Modify : `backend/app/api/imports.py`
- Create : `backend/alembic/versions/20260507_2010_e2_import_sha256_unique.py`
- Create : `backend/tests/test_e2_import_idempotence.py`

**Pourquoi :** Un double-clic ou un retry réseau peut créer deux `ImportRecord` pour le même fichier PDF, doublant les transactions. Le SHA-256 est déjà calculé et stocké dans `file_sha256` (indexé). Il manque un index unique et le check dans l'API.

**Steps :**

- [ ] **Step 1 : Test qui échoue**

Créer `backend/tests/test_e2_import_idempotence.py` :

```python
"""E2 — Idempotence upload : même SHA-256 → même import_id, pas de doublon."""
import io
import pytest
from unittest.mock import patch, MagicMock
from app.models.import_record import ImportRecord
from sqlalchemy import select


def test_double_upload_same_file_returns_existing(client, db_session, admin_auth_headers, bank_account_factory):
    ba = bank_account_factory()
    fake_pdf = b"%PDF-1.4 fake-content"

    mock_rec = MagicMock(spec=ImportRecord)
    mock_rec.id = 99
    mock_rec.file_sha256 = "abc123"

    with patch("app.api.imports.import_pdf_bytes", return_value=mock_rec) as mock_import:
        # Premier upload
        resp1 = client.post(
            "/api/imports",
            files={"file": ("statement.pdf", io.BytesIO(fake_pdf), "application/pdf")},
            data={"bank_account_id": ba.id},
            headers=admin_auth_headers,
        )
    assert resp1.status_code == 201
    import_id_1 = resp1.json()["id"]

    # Second upload du même fichier
    resp2 = client.post(
        "/api/imports",
        files={"file": ("statement.pdf", io.BytesIO(fake_pdf), "application/pdf")},
        data={"bank_account_id": ba.id},
        headers=admin_auth_headers,
    )
    assert resp2.status_code == 200  # pas 201
    import_id_2 = resp2.json()["id"]
    assert import_id_1 == import_id_2
```

```bash
docker exec horizon-backend-1 pytest backend/tests/test_e2_import_idempotence.py -v
# Attendu : FAILED
```

- [ ] **Step 2 : Migration contrainte unique**

Créer `backend/alembic/versions/20260507_2010_e2_import_sha256_unique.py` :

```python
"""E2 — Contrainte unique (bank_account_id, file_sha256) sur import_records.

Revision ID: h0r1z0ne0200
Revises: h0r1z0ne0100
Create Date: 2026-05-07 20:10:00

CONCURRENTLY non supporté dans une transaction Alembic — exécution hors
transaction (execute_timeout=None). On gère le cas où l'index existe déjà
via IF NOT EXISTS.
"""
from __future__ import annotations
from alembic import op

revision = "h0r1z0ne0200"
down_revision = "h0r1z0ne0100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Pas de CREATE UNIQUE INDEX CONCURRENTLY dans une transaction alembic par défaut.
    # On utilise un index ordinaire (table petite, downtime négligeable en prod).
    op.create_index(
        "uq_import_records_account_sha256",
        "import_records",
        ["bank_account_id", "file_sha256"],
        unique=True,
        postgresql_where="file_sha256 IS NOT NULL",  # exclut les imports sans SHA (cas legacy)
    )


def downgrade() -> None:
    op.drop_index("uq_import_records_account_sha256", table_name="import_records")
```

Appliquer :
```bash
docker cp backend/alembic/versions/20260507_2010_e2_import_sha256_unique.py \
    horizon-backend-1:/app/alembic/versions/
docker exec horizon-backend-1 alembic upgrade head
```

- [ ] **Step 3 : Modifier backend/app/api/imports.py**

Dans `create_import`, après la lecture du contenu et la vérification MIME, avant l'appel à `import_pdf_bytes`, insérer le check SHA-256 :

```python
import hashlib
from fastapi import status as http_status

# … dans create_import(), après la vérification MIME :

    # Idempotence : si un ImportRecord pour ce (bank_account, sha256) existe déjà,
    # retourner l'existant en 200 (pas 201) sans réinsérer les transactions.
    sha256 = hashlib.sha256(content).hexdigest()
    existing = session.execute(
        select(ImportRecord).where(
            ImportRecord.bank_account_id == bank_account_id,
            ImportRecord.file_sha256 == sha256,
        )
    ).scalar_one_or_none()
    if existing is not None:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            content=ImportRecordRead.model_validate(existing).model_dump(mode="json"),
            status_code=200,
        )
```

Le type de retour de l'endpoint doit rester `ImportRecordRead` ; ajouter `Response` dans les imports si nécessaire. L'endpoint garde `status_code=201` sur son décorateur — le `JSONResponse(status_code=200)` override proprement.

- [ ] **Step 4 : Test vert**

```bash
docker exec horizon-backend-1 pytest backend/tests/test_e2_import_idempotence.py -v
# Attendu : 1 passed
```

- [ ] **Step 5 : Commit**

```
feat(imports): E2 — idempotence SHA-256 (double upload → 200 + import existant)

Avant d'appeler import_pdf_bytes, l'API vérifie si un ImportRecord avec le
même (bank_account_id, file_sha256) existe. Si oui → retourne l'existant
en 200 OK. Index unique PostgreSQL en garde-fou supplémentaire.

Co-authored-by: Claude <noreply@anthropic.com>
```

---

## Task E3 — Aperçu live debounced dans RuleForm

**Files :**
- Modify : `frontend/src/components/RuleForm.tsx`
- Modify : `frontend/src/content/documentation.ts`

**Pourquoi :** Forcer un clic "Aperçu" pour tester une règle crée une friction inutile. Un debounce 450 ms déclenche l'aperçu automatiquement à chaque modification de filtre, rendant le feedback immédiat.

**Steps :**

- [ ] **Step 1 : Test Vitest qui échoue**

Dans `frontend/src/components/RuleForm.test.tsx` (créer si absent) :

```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { RuleForm } from './RuleForm';
import * as rulesApi from '@/api/rules';

vi.mock('@/api/rules', async (importOriginal) => {
  const actual = await importOriginal<typeof rulesApi>();
  return { ...actual, previewRule: vi.fn().mockResolvedValue({ matching_count: 0, sample: [] }) };
});

it('déclenche previewRule automatiquement après debounce 450ms', async () => {
  vi.useFakeTimers();
  render(<RuleForm categories={[]} entities={[]} counterparties={[]} bankAccounts={[]} initialValue={null} onSubmit={vi.fn()} onCancel={vi.fn()} />);
  fireEvent.change(screen.getByLabelText(/valeur/i), { target: { value: 'AGICAP' } });
  expect(rulesApi.previewRule).not.toHaveBeenCalled();
  vi.advanceTimersByTime(450);
  await waitFor(() => expect(rulesApi.previewRule).toHaveBeenCalledTimes(1));
  vi.useRealTimers();
});
```

```bash
cd frontend && npx vitest --run src/components/RuleForm.test.tsx
# Attendu : FAILED
```

- [ ] **Step 2 : Modifier RuleForm.tsx**

Remplacer la gestion du preview dans `RuleForm.tsx` :

1. Ajouter en tête de fichier :
```typescript
import { useEffect, useRef } from "react";
```

2. Après la déclaration des états existants, ajouter :
```typescript
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Debounce aperçu : se déclenche 450 ms après la dernière modification d'un filtre.
  // Les dépendances couvrent tous les champs qui influencent le résultat du preview.
  useEffect(() => {
    // Pas d'aperçu automatique si aucun filtre n'est défini (évite un appel à vide
    // à l'ouverture du tiroir, qui retournerait toutes les transactions).
    const hasFilter = labelValue || counterpartyId || bankAccountId || amountOp || direction !== "ANY";
    if (!hasFilter) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      const resp = await previewRule(buildPayload());
      setPreview(resp);
    }, 450);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [labelOp, labelValue, direction, amountOp, amountVal, amountVal2, counterpartyId, bankAccountId, entityId]);
```

3. Le bouton "Aperçu" existant conserve son handler `handlePreview` pour un refresh forcé. Lui ajouter un tooltip :
```tsx
<Button type="button" variant="outline" size="sm" onClick={handlePreview} title="Rafraîchir l'aperçu manuellement">
  Aperçu
</Button>
```

- [ ] **Step 3 : Mettre à jour documentation.ts — section regles**

Dans `DOC_SECTIONS`, section `id: "regles"`, dans `does`, remplacer la phrase sur le bouton Aperçu par :

> "Pour tester une règle : l'aperçu se met à jour automatiquement (délai de 0,5 secondes) dès que vous modifiez un filtre. Vous pouvez aussi cliquer sur le bouton Aperçu pour forcer un rafraîchissement immédiat."

Ajouter une entrée `FeatureDoc` pour l'aperçu auto :

```typescript
export const FEATURE_DOCS: FeatureDoc[] = [
  // … docs existants …
  {
    id: "apercu-live-regles",
    title: "Aperçu automatique dans le formulaire de règle",
    whatItDoes: "Affiche en temps réel les transactions qui seraient capturées par la règle en cours de configuration.",
    whatItChanges: [
      "Déclenche automatiquement un appel GET /api/rules/preview 450 ms après la dernière modification d'un filtre.",
      "Met à jour la liste d'aperçu dans le tiroir sans action manuelle.",
    ],
    whatItDoesNotChange: [
      "Ne crée aucune règle, ne catégorise aucune transaction.",
      "Le bouton Aperçu reste disponible pour un rafraîchissement forcé.",
    ],
    whenToUse: [
      "Quand vous ajustez un libellé et souhaitez voir immédiatement l'impact sans cliquer.",
    ],
  },
];
```

- [ ] **Step 4 : Test vert**

```bash
cd frontend && npx vitest --run src/components/RuleForm.test.tsx
# Attendu : passed
cd frontend && npx tsc -b
```

- [ ] **Step 5 : Commit**

```
feat(rules): E3 — aperçu live debounced 450ms dans RuleForm + doc d'impact

L'aperçu se déclenche automatiquement après chaque modification de filtre
(délai 450ms). Le bouton Aperçu reste pour le refresh forcé.
Mise à jour documentation.ts section regles.

Co-authored-by: Claude <noreply@anthropic.com>
```

---

## Task E4 — Auto-suggestion de règle après N catégorisations manuelles identiques

**Files :**
- Modify : `backend/app/api/rules.py`
- Create : `backend/tests/test_e4_auto_suggest.py`
- Modify : `frontend/src/api/rules.ts`
- Modify : `frontend/src/pages/TransactionsPage.tsx`
- Modify : `frontend/src/content/documentation.ts`

**Pourquoi :** Quand un utilisateur catégorise manuellement 3 transactions portant le même normalized_label, il fait implicitement une règle. Lui proposer de créer cette règle réduit le travail manuel futur et augmente le taux de couverture automatique. Approche backend-driven choisie : robuste multi-session, pas d'état volatile frontend.

**Steps :**

- [ ] **Step 1 : Test backend qui échoue**

Créer `backend/tests/test_e4_auto_suggest.py` :

```python
"""E4 — GET /api/rules/auto-suggest retourne les patterns manuels répétés."""
import pytest
from datetime import datetime, timedelta


def seed_manual_audit_entries(db_session, user, label: str, category_id: int, count: int = 3):
    """Insère <count> entrées audit de type MANUAL pour le même label."""
    from app.models.audit_log import AuditLog
    for i in range(count):
        db_session.add(AuditLog(
            user_id=user.id,
            action="update",
            entity_type="Transaction",
            entity_id=str(1000 + i),
            after_json={"categorized_by": "MANUAL", "normalized_label": label, "category_id": category_id},
            occurred_at=datetime.utcnow() - timedelta(days=i),
        ))
    db_session.commit()


def test_auto_suggest_returns_pattern(client, db_session, admin_user, admin_auth_headers, category_factory):
    cat = category_factory(name="Test catégorie")
    seed_manual_audit_entries(db_session, admin_user, "PRLV AGICAP", cat.id, count=3)
    resp = client.get("/api/rules/auto-suggest", headers=admin_auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    labels = [s["normalized_label"] for s in data]
    assert "PRLV AGICAP" in labels


def test_auto_suggest_requires_min_3(client, db_session, admin_user, admin_auth_headers, category_factory):
    cat = category_factory(name="Test catégorie 2")
    seed_manual_audit_entries(db_session, admin_user, "PRLV UNIQUEMENT 2X", cat.id, count=2)
    resp = client.get("/api/rules/auto-suggest", headers=admin_auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    labels = [s["normalized_label"] for s in data]
    assert "PRLV UNIQUEMENT 2X" not in labels
```

```bash
docker exec horizon-backend-1 pytest backend/tests/test_e4_auto_suggest.py -v
# Attendu : FAILED
```

- [ ] **Step 2 : Ajouter endpoint GET /api/rules/auto-suggest dans rules.py**

Avant le routeur `GET /preview`, ajouter (avant les routes dynamiques pour éviter les conflits de path) :

```python
from datetime import datetime, timedelta
from sqlalchemy import func as sqlfunc


class AutoSuggestItem(BaseModel):
    normalized_label: str
    category_id: int
    category_name: str
    manual_count: int


@router.get("/auto-suggest", response_model=list[AutoSuggestItem])
def auto_suggest(
    entity_id: int | None = Query(default=None),
    min_count: int = Query(default=3, ge=2, le=20),
    days: int = Query(default=30, ge=7, le=90),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[AutoSuggestItem]:
    """Retourne les patterns manuels répétés qui méritent une règle automatique.

    Interroge audit_log pour les actions 'update' sur Transaction avec
    categorized_by='MANUAL' dans les <days> derniers jours. Regroupe par
    (normalized_label, category_id), filtre >= min_count occurrences.
    Exclut les patterns déjà couverts par une règle existante (label_value
    CONTAINS ou EQUALS normalized_label).
    """
    from app.models.audit_log import AuditLog
    from app.models.category import Category

    since = datetime.utcnow() - timedelta(days=days)

    # Requête brute sur le champ after_json (JSONB).
    rows = session.execute(
        select(
            AuditLog.after_json["normalized_label"].astext.label("norm_label"),
            AuditLog.after_json["category_id"].astext.cast(sa.Integer).label("cat_id"),
            sqlfunc.count(AuditLog.id).label("cnt"),
        )
        .where(
            AuditLog.action == "update",
            AuditLog.entity_type == "Transaction",
            AuditLog.after_json["categorized_by"].astext == "MANUAL",
            AuditLog.after_json["normalized_label"].astext.isnot(None),
            AuditLog.occurred_at >= since,
        )
        .group_by("norm_label", "cat_id")
        .having(sqlfunc.count(AuditLog.id) >= min_count)
        .order_by(sqlfunc.count(AuditLog.id).desc())
        .limit(10)
    ).all()

    if not rows:
        return []

    cat_ids = {r.cat_id for r in rows}
    cats = {c.id: c.name for c in session.execute(
        select(Category).where(Category.id.in_(cat_ids))
    ).scalars().all()}

    # Filtrer les labels déjà couverts par une règle active (heuristique simple).
    existing_label_values = set(session.execute(
        select(CategorizationRule.label_value).where(
            CategorizationRule.label_value.isnot(None)
        )
    ).scalars().all())

    result = []
    for r in rows:
        if r.norm_label and any(
            r.norm_label.upper() in (lv or "").upper()
            for lv in existing_label_values
        ):
            continue
        result.append(AutoSuggestItem(
            normalized_label=r.norm_label,
            category_id=r.cat_id,
            category_name=cats.get(r.cat_id, f"#{r.cat_id}"),
            manual_count=r.cnt,
        ))

    return result
```

Ajouter `import sqlalchemy as sa` en tête de fichier si absent.

- [ ] **Step 3 : Test vert backend**

```bash
docker exec horizon-backend-1 pytest backend/tests/test_e4_auto_suggest.py -v
# Attendu : 2 passed
```

- [ ] **Step 4 : Client TS + hook**

Dans `frontend/src/api/rules.ts`, ajouter :

```typescript
export interface AutoSuggestItem {
  normalized_label: string;
  category_id: number;
  category_name: string;
  manual_count: number;
}

export function fetchAutoSuggest(entityId?: number): Promise<AutoSuggestItem[]> {
  const params = entityId ? `?entity_id=${entityId}` : "";
  return apiFetch<AutoSuggestItem[]>(`/api/rules/auto-suggest${params}`);
}

export function useAutoSuggest(entityId?: number) {
  return useQuery({
    queryKey: ["rules", "auto-suggest", entityId],
    queryFn: () => fetchAutoSuggest(entityId),
    staleTime: 60_000,
  });
}
```

- [ ] **Step 5 : Toaster dans TransactionsPage.tsx**

Après le chargement des données, ajouter le hook et l'affichage conditionnel. Dans le corps de `TransactionsPage` :

```typescript
import { useAutoSuggest } from "@/api/rules";

// … dans le composant :
const autoSuggestQuery = useAutoSuggest(entityId ?? undefined);
const suggestions = autoSuggestQuery.data ?? [];
const [dismissedSuggestions, setDismissedSuggestions] = useState<Set<string>>(new Set());

const visibleSuggestions = suggestions.filter(
  (s) => !dismissedSuggestions.has(s.normalized_label)
);
```

Afficher un bandeau juste sous l'en-tête de page (au-dessus des filtres) si `visibleSuggestions.length > 0` :

```tsx
{visibleSuggestions.length > 0 && (
  <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-[13px] text-amber-900 space-y-1">
    {visibleSuggestions.slice(0, 3).map((s) => (
      <div key={s.normalized_label} className="flex items-center justify-between gap-4">
        <span>
          Vous avez catégorisé {s.manual_count} fois{" "}
          <span className="font-mono font-semibold">{s.normalized_label}</span>{" "}
          en <span className="font-semibold">{s.category_name}</span>. Créer une règle automatique ?
        </span>
        <div className="flex gap-2 shrink-0">
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              setRuleInitialValue({
                name: `Règle — ${s.normalized_label.slice(0, 40)}`,
                label_operator: "CONTAINS",
                label_value: s.normalized_label,
                category_id: s.category_id,
                direction: "ANY",
                entity_id: entityId ?? null,
              } as RuleSuggestion);
              setRuleDrawerOpen(true);
            }}
          >
            Créer une règle
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() =>
              setDismissedSuggestions((prev) => new Set([...prev, s.normalized_label]))
            }
          >
            Ignorer
          </Button>
        </div>
      </div>
    ))}
  </div>
)}
```

- [ ] **Step 6 : Documentation d'impact**

Ajouter dans `documentation.ts` une `FeatureDoc` pour `id: "auto-suggest-regle"` et mettre à jour la section `transactions` (dans `does`) :

> "Quand vous avez catégorisé manuellement le même libellé au moins 3 fois dans la même catégorie lors des 30 derniers jours, un bandeau apparaît en haut de la page Transactions et vous propose de créer une règle automatique. Le bouton 'Créer une règle' ouvre le formulaire pré-rempli. Le bouton 'Ignorer' masque la suggestion pour la session en cours."

- [ ] **Step 7 : Test Vitest**

```bash
cd frontend && npx tsc -b
cd frontend && npx vitest --run
```

- [ ] **Step 8 : Commit**

```
feat(rules): E4 — auto-suggestion de règle après 3 catégorisations manuelles identiques

Backend : GET /api/rules/auto-suggest interroge audit_log sur 30 jours,
regroupe par (normalized_label, category_id), retourne les patterns >= 3x
non déjà couverts par une règle.
Frontend : bandeau contextuel dans TransactionsPage avec bouton pré-remplissant
RuleForm. Doc d'impact transactions + FeatureDoc.

Co-authored-by: Claude <noreply@anthropic.com>
```

---

## Task E5 — Page admin pour client_errors

**Files :**
- Create : `backend/alembic/versions/20260507_2020_e5_client_error_acknowledged.py`
- Modify : `backend/app/models/client_error.py`
- Modify : `backend/app/schemas/client_error.py`
- Modify : `backend/app/api/admin_client_errors.py`
- Create : `backend/tests/test_e5_client_errors_admin.py`
- Create : `frontend/src/pages/AdminClientErrorsPage.tsx`
- Create : `frontend/src/api/clientErrors.ts`
- Modify : `frontend/src/router.tsx`
- Modify : `frontend/src/components/Sidebar.tsx`
- Modify : `frontend/src/content/documentation.ts`

**Pourquoi :** L'endpoint `GET /api/admin/client-errors` existe depuis le Plan F mais aucune page UI ne l'exploite. Les erreurs JS remontées par les utilisateurs ne sont pas visibles sans outil CLI. Une page dédiée permet de suivre et acquitter les incidents sans accès SSH.

**Steps :**

- [ ] **Step 1 : Test backend qui échoue**

Créer `backend/tests/test_e5_client_errors_admin.py` :

```python
"""E5 — Tests de la page admin client_errors : liste, filtres, acquittement."""
import pytest
from datetime import datetime


def create_error(db_session, user_id=None, message="test error", severity="error"):
    from app.models.client_error import ClientError
    ce = ClientError(
        user_id=user_id,
        severity=severity,
        source="manual",
        message=message,
        occurred_at=datetime.utcnow(),
    )
    db_session.add(ce)
    db_session.commit()
    db_session.refresh(ce)
    return ce


def test_list_client_errors(client, db_session, admin_auth_headers):
    ce = create_error(db_session, message="kaboom")
    resp = client.get("/api/admin/client-errors", headers=admin_auth_headers)
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["items"]]
    assert ce.id in ids


def test_acknowledge_client_error(client, db_session, admin_auth_headers):
    ce = create_error(db_session, message="to acknowledge")
    resp = client.patch(
        f"/api/admin/client-errors/{ce.id}/acknowledge",
        headers=admin_auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["acknowledged_at"] is not None

    # Vérifier en DB
    db_session.refresh(ce)
    assert ce.acknowledged_at is not None


def test_filter_acknowledged(client, db_session, admin_auth_headers):
    ce_open = create_error(db_session, message="open")
    ce_ack = create_error(db_session, message="acked")
    client.patch(f"/api/admin/client-errors/{ce_ack.id}/acknowledge", headers=admin_auth_headers)

    resp = client.get("/api/admin/client-errors?acknowledged=false", headers=admin_auth_headers)
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["items"]]
    assert ce_open.id in ids
    assert ce_ack.id not in ids
```

```bash
docker exec horizon-backend-1 pytest backend/tests/test_e5_client_errors_admin.py -v
# Attendu : FAILED (colonne acknowledged_at absente + PATCH absent)
```

- [ ] **Step 2 : Migration**

Créer `backend/alembic/versions/20260507_2020_e5_client_error_acknowledged.py` :

```python
"""E5 — Ajout colonne acknowledged_at sur client_errors.

Revision ID: h0r1z0ne0500
Revises: h0r1z0ne0200
Create Date: 2026-05-07 20:20:00
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "h0r1z0ne0500"
down_revision = "h0r1z0ne0200"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "client_errors",
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("client_errors", "acknowledged_at")
```

Appliquer :
```bash
docker cp backend/alembic/versions/20260507_2020_e5_client_error_acknowledged.py \
    horizon-backend-1:/app/alembic/versions/
docker exec horizon-backend-1 alembic upgrade head
```

- [ ] **Step 3 : Modifier le modèle ClientError**

Dans `backend/app/models/client_error.py`, ajouter après `request_id` :

```python
from datetime import datetime
# …
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
```

- [ ] **Step 4 : Modifier les schémas et l'API**

Dans `backend/app/schemas/client_error.py` :
- Ajouter `acknowledged_at: datetime | None = None` dans `ClientErrorRead`.
- Ajouter une classe :

```python
class ClientErrorAcknowledgeResponse(BaseModel):
    id: int
    acknowledged_at: datetime
```

Dans `backend/app/api/admin_client_errors.py` :
- Ajouter `acknowledged: bool | None = Query(default=None)` comme paramètre de `list_client_errors` et le filtre correspondant :

```python
if acknowledged is True:
    base = base.where(ClientError.acknowledged_at.isnot(None))
    count_base = count_base.where(ClientError.acknowledged_at.isnot(None))
elif acknowledged is False:
    base = base.where(ClientError.acknowledged_at.is_(None))
    count_base = count_base.where(ClientError.acknowledged_at.is_(None))
```

- Ajouter l'import `datetime` et le nouveau endpoint :

```python
from datetime import datetime as dt_datetime

@router.patch("/{error_id}/acknowledge", response_model=ClientErrorAcknowledgeResponse)
def acknowledge_client_error(
    error_id: int,
    db: Session = Depends(get_db),
) -> ClientErrorAcknowledgeResponse:
    ce = db.get(ClientError, error_id)
    if ce is None:
        raise HTTPException(status_code=404, detail="Erreur introuvable")
    ce.acknowledged_at = dt_datetime.utcnow()
    db.commit()
    db.refresh(ce)
    return ClientErrorAcknowledgeResponse(id=ce.id, acknowledged_at=ce.acknowledged_at)
```

- [ ] **Step 5 : Test vert backend**

```bash
docker exec horizon-backend-1 pytest backend/tests/test_e5_client_errors_admin.py -v
# Attendu : 3 passed
```

- [ ] **Step 6 : Client TS**

Créer `frontend/src/api/clientErrors.ts` :

```typescript
import { apiFetch } from "./client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

export interface ClientErrorItem {
  id: number;
  occurred_at: string;
  user_id: number | null;
  user_email: string | null;
  severity: string;
  source: string;
  message: string;
  stack: string | null;
  url: string | null;
  user_agent: string | null;
  request_id: string | null;
  context_json: Record<string, unknown> | null;
  acknowledged_at: string | null;
}

export interface ClientErrorListResponse {
  items: ClientErrorItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface ClientErrorFilters {
  severity?: string;
  acknowledged?: boolean;
  since?: string;
  until?: string;
  limit?: number;
  offset?: number;
}

export function fetchClientErrors(filters: ClientErrorFilters = {}): Promise<ClientErrorListResponse> {
  const p = new URLSearchParams();
  if (filters.severity) p.set("severity", filters.severity);
  if (filters.acknowledged !== undefined) p.set("acknowledged", String(filters.acknowledged));
  if (filters.since) p.set("since", filters.since);
  if (filters.until) p.set("until", filters.until);
  if (filters.limit) p.set("limit", String(filters.limit));
  if (filters.offset) p.set("offset", String(filters.offset));
  const qs = p.toString();
  return apiFetch<ClientErrorListResponse>(`/api/admin/client-errors${qs ? `?${qs}` : ""}`);
}

export function useClientErrors(filters: ClientErrorFilters = {}) {
  return useQuery({
    queryKey: ["admin", "client-errors", filters],
    queryFn: () => fetchClientErrors(filters),
  });
}

export function useAcknowledgeClientError() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch<{ id: number; acknowledged_at: string }>(`/api/admin/client-errors/${id}/acknowledge`, {
        method: "PATCH",
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "client-errors"] }),
  });
}
```

- [ ] **Step 7 : Créer AdminClientErrorsPage.tsx**

Créer `frontend/src/pages/AdminClientErrorsPage.tsx` avec :
- En-tête avec titre "Erreurs client", sous-titre "Erreurs JavaScript remontées automatiquement par les navigateurs des utilisateurs."
- Bandeau d'introduction permanent (concept nouveau) : "Cette page liste les erreurs JavaScript survenues dans le navigateur des utilisateurs. Chaque entrée correspond à une exception non interceptée, un appel API échoué ou une erreur remontée manuellement. Vous pouvez les acquitter une fois traitées."
- Filtres : sélect Gravité (toutes / error / warning / fatal), toggle "Non acquittées uniquement", inputs Depuis / Jusqu'au.
- Tableau : id, occurred_at (formaté fr-FR), user_email (ou "anonyme"), severity (badge coloré selon niveau), message (tronqué 80 chars, full au survol via `title`), url (tronquée), action "Marquer acquitté" (bouton disabled si `acknowledged_at` non null, badge "Acquitté" affiché à la place).
- Pagination simple (boutons Précédent / Suivant, `limit=50`).
- Tooltip HelpTooltip sur l'action "Marquer acquitté" : "Indique que cette erreur a été examinée et traitée. Ne supprime pas l'entrée."

```tsx
// Squelette minimal — à compléter :
export function AdminClientErrorsPage() {
  const [filters, setFilters] = useState<ClientErrorFilters>({ limit: 50, offset: 0 });
  const query = useClientErrors(filters);
  const ackMut = useAcknowledgeClientError();
  const items = query.data?.items ?? [];
  const total = query.data?.total ?? 0;

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight text-ink">Erreurs client</h1>
        <p className="mt-0.5 text-[13px] text-muted-foreground">
          Erreurs JavaScript remontées automatiquement par les navigateurs des utilisateurs.
        </p>
      </div>
      <div
        role="note"
        className="rounded-md border border-blue-200 bg-blue-50 px-4 py-3 text-[13px] text-blue-900"
      >
        Cette page liste les erreurs JavaScript survenues dans le navigateur des utilisateurs.
        Chaque entrée correspond à une exception non interceptée, un appel API échoué ou une
        erreur remontée manuellement. Acquittez une erreur une fois qu'elle a été examinée et
        traitée.
      </div>
      {/* Filtres, tableau, pagination — implémenter selon le pattern AdminAuditLogPage */}
    </section>
  );
}
```

Implémenter le tableau en s'inspirant du pattern `AdminAuditLogPage.tsx` (filtres en ligne, tableau avec actions, pagination offset).

- [ ] **Step 8 : Router + Sidebar**

Dans `frontend/src/router.tsx`, ajouter après la route `/administration/audit` :

```tsx
const AdminClientErrorsPage = lazy(() =>
  import('@/pages/AdminClientErrorsPage').then((m) => ({ default: m.AdminClientErrorsPage })),
);

// Dans le tableau des routes :
{
  path: '/administration/erreurs-client',
  element: (
    <AdminRoute>
      <LazyPage>
        <AdminClientErrorsPage />
      </LazyPage>
    </AdminRoute>
  ),
},
```

Dans `frontend/src/components/Sidebar.tsx`, ajouter après l'entrée Journal d'audit :

```tsx
{
  to: '/administration/erreurs-client',
  label: 'Erreurs client',
  icon: icon(
    <>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 8v4" />
      <path d="M12 16h.01" />
    </>,
  ),
  adminOnly: true,
},
```

- [ ] **Step 9 : Documentation d'impact**

Ajouter dans `DOC_SECTIONS` une nouvelle section `id: "administration-erreurs-client"` et une `FeatureDoc` pour l'action "Marquer acquitté". Mettre à jour la section `id: "administration"` pour mentionner la page.

- [ ] **Step 10 : TypeScript + Vitest**

```bash
cd frontend && npx tsc -b
cd frontend && npx vitest --run
```

- [ ] **Step 11 : Commit**

```
feat(admin): E5 — page admin erreurs client avec filtres et acquittement

Ajoute colonne acknowledged_at (migration h0r1z0ne0500), endpoint PATCH
/api/admin/client-errors/{id}/acknowledge, page AdminClientErrorsPage +
route /administration/erreurs-client + entrée sidebar. Filtre acknowledged=
true/false dans le listing. Doc d'impact CLAUDE.md.

Co-authored-by: Claude <noreply@anthropic.com>
```

---

## Task E6 — Bulk "select all results" sur transactions filtrées

**Files :**
- Modify : `backend/app/api/transactions.py`
- Modify : `backend/app/schemas/categorization_rule.py`
- Create : `backend/tests/test_e6_bulk_categorize_filtered.py`
- Modify : `frontend/src/api/transactions.ts`
- Modify : `frontend/src/pages/TransactionsPage.tsx`
- Modify : `frontend/src/components/transactions/BulkCategorizationDrawer.tsx`
- Modify : `frontend/src/content/documentation.ts`

**Pourquoi :** La sélection est actuellement limitée à la page courante (max 50 lignes). Pour catégoriser 400 transactions non catégorisées en masse, l'utilisateur devrait changer de page 8 fois. Un endpoint `bulk-categorize-filtered` résout ce point d'un seul appel backend.

**Steps :**

- [ ] **Step 1 : Test backend qui échoue**

Créer `backend/tests/test_e6_bulk_categorize_filtered.py` :

```python
"""E6 — POST /api/transactions/bulk-categorize-filtered catégorise via filtres."""
import pytest
from app.models.transaction import Transaction, TransactionCategorizationSource
from sqlalchemy import select


def test_bulk_categorize_filtered_uncategorized(
    client, db_session, admin_auth_headers, entity_factory, bank_account_factory,
    transaction_factory, category_factory
):
    entity = entity_factory()
    ba = bank_account_factory(entity_id=entity.id)
    cat = category_factory(name="Charges test")
    tx1 = transaction_factory(bank_account_id=ba.id, label="PRLV TEST", categorized_by="NONE")
    tx2 = transaction_factory(bank_account_id=ba.id, label="PRLV TEST 2", categorized_by="NONE")
    tx3 = transaction_factory(bank_account_id=ba.id, label="AUTRE", categorized_by="MANUAL")

    resp = client.post(
        "/api/transactions/bulk-categorize-filtered",
        json={
            "category_id": cat.id,
            "entity_id": entity.id,
            "uncategorized": True,
        },
        headers=admin_auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["updated_count"] == 2  # tx1 + tx2, pas tx3

    db_session.refresh(tx1)
    db_session.refresh(tx3)
    assert tx1.category_id == cat.id
    assert tx3.category_id != cat.id  # tx3 non modifiée


def test_bulk_categorize_filtered_reader_forbidden(client, reader_auth_headers):
    resp = client.post(
        "/api/transactions/bulk-categorize-filtered",
        json={"category_id": 1},
        headers=reader_auth_headers,
    )
    assert resp.status_code == 403
```

```bash
docker exec horizon-backend-1 pytest backend/tests/test_e6_bulk_categorize_filtered.py -v
# Attendu : FAILED
```

- [ ] **Step 2 : Ajouter BulkCategorizeFilteredRequest dans les schémas**

Dans `backend/app/schemas/categorization_rule.py`, ajouter :

```python
from datetime import date as date_type
from decimal import Decimal

class BulkCategorizeFilteredRequest(BaseModel):
    category_id: int
    entity_id: int | None = None
    bank_account_id: int | None = None
    date_from: date_type | None = None
    date_to: date_type | None = None
    counterparty_id: int | None = None
    search: str | None = None
    uncategorized: bool | None = None
    include_sepa_children: bool = False
    amount_min: Decimal | None = None
    amount_max: Decimal | None = None
```

- [ ] **Step 3 : Ajouter l'endpoint dans transactions.py**

Après `bulk_categorize`, ajouter :

```python
from app.schemas.categorization_rule import BulkCategorizeFilteredRequest, BulkCategorizeRequest

@router.post("/bulk-categorize-filtered")
def bulk_categorize_filtered(
    payload: BulkCategorizeFilteredRequest,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> dict[str, int]:
    if user.role == UserRole.READER:
        raise HTTPException(status_code=403, detail="Droits éditeur requis")

    cat = session.get(Category, payload.category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")

    accessible_entity_ids = accessible_entity_ids_subquery(session=session, user=user)

    conditions = [
        BankAccount.entity_id.in_(accessible_entity_ids),
        Transaction.is_aggregation_parent.is_(False),
    ]
    if not payload.include_sepa_children:
        conditions.append(Transaction.parent_transaction_id.is_(None))
    if payload.entity_id is not None:
        require_entity_access(session=session, user=user, entity_id=payload.entity_id)
        conditions.append(BankAccount.entity_id == payload.entity_id)
    if payload.bank_account_id:
        conditions.append(Transaction.bank_account_id == payload.bank_account_id)
    if payload.date_from:
        conditions.append(Transaction.operation_date >= payload.date_from)
    if payload.date_to:
        conditions.append(Transaction.operation_date <= payload.date_to)
    if payload.counterparty_id:
        conditions.append(Transaction.counterparty_id == payload.counterparty_id)
    if payload.search:
        like = f"%{payload.search.lower()}%"
        conditions.append(
            or_(func.lower(Transaction.label).like(like), func.lower(Transaction.raw_label).like(like))
        )
    if payload.uncategorized:
        conditions.append(Transaction.categorized_by == TransactionCategorizationSource.NONE)
    if payload.amount_min is not None:
        conditions.append(func.abs(Transaction.amount) >= payload.amount_min)
    if payload.amount_max is not None:
        conditions.append(func.abs(Transaction.amount) <= payload.amount_max)

    txs = session.execute(
        select(Transaction)
        .join(BankAccount, BankAccount.id == Transaction.bank_account_id)
        .where(and_(*conditions))
    ).scalars().all()

    for tx in txs:
        tx.category_id = payload.category_id
        tx.categorized_by = TransactionCategorizationSource.MANUAL

    if txs:
        record_batch_audit(
            session, user=user, request=request,
            action="update", entity_type="Transaction",
            entity_id=f"bulk-filtered({len(txs)})",
            after={
                "operation": "bulk_categorize_filtered",
                "filters": payload.model_dump(exclude={"category_id"}),
                "category_id": payload.category_id,
                "count": len(txs),
            },
        )
    session.commit()
    return {"updated_count": len(txs)}
```

- [ ] **Step 4 : Test vert backend**

```bash
docker exec horizon-backend-1 pytest backend/tests/test_e6_bulk_categorize_filtered.py -v
# Attendu : 2 passed
```

- [ ] **Step 5 : Client TS + hook**

Dans `frontend/src/api/transactions.ts`, ajouter :

```typescript
export interface BulkCategorizeFilteredPayload {
  category_id: number;
  entity_id?: number;
  bank_account_id?: number;
  date_from?: string;
  date_to?: string;
  counterparty_id?: number;
  search?: string;
  uncategorized?: boolean;
  include_sepa_children?: boolean;
  amount_min?: number;
  amount_max?: number;
}

export function bulkCategorizeFiltered(payload: BulkCategorizeFilteredPayload): Promise<{ updated_count: number }> {
  return apiFetch<{ updated_count: number }>("/api/transactions/bulk-categorize-filtered", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function useBulkCategorizeFiltered() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: bulkCategorizeFiltered,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["transactions"] }),
  });
}
```

- [ ] **Step 6 : Checkbox "Sélectionner tous les X résultats" dans TransactionsPage**

Ajouter dans la toolbar de sélection (au-dessus du tableau, visible quand des transactions sont sélectionnées ou quand la page est pleine) :

```tsx
{allSelected && (data?.total ?? 0) > items.length && (
  <button
    type="button"
    className="text-[12.5px] text-blue-700 underline hover:no-underline"
    onClick={() => setSelectAllFiltered(true)}
  >
    Sélectionner les {data?.total} résultats correspondant aux filtres actuels
  </button>
)}
{selectAllFiltered && (
  <span className="text-[12.5px] text-blue-700">
    Les {data?.total} résultats sont sélectionnés.{" "}
    <button
      type="button"
      className="underline hover:no-underline"
      onClick={() => setSelectAllFiltered(false)}
    >
      Annuler
    </button>
  </span>
)}
```

Ajouter `const [selectAllFiltered, setSelectAllFiltered] = useState(false)` dans l'état local. Passer `selectAllFiltered` et `queryFilters` au `BulkCategorizationDrawer` pour que le submit utilise `bulkCategorizeFiltered` au lieu de `bulkCategorize` quand ce flag est actif.

- [ ] **Step 7 : Documentation d'impact**

Dans `documentation.ts`, section `transactions`, dans `does`, ajouter :

> "Pour catégoriser toutes les transactions d'un filtre en une seule action (sans limites de page) : sélectionnez toutes les transactions de la page courante avec la case en en-tête de tableau, puis cliquez sur le lien 'Sélectionner les X résultats correspondant aux filtres actuels' qui apparaît. Le drawer de catégorisation s'applique alors à l'ensemble du résultat filtré."

Ajouter une `FeatureDoc` pour `id: "bulk-categorize-filtre"`.

- [ ] **Step 8 : TypeScript + Vitest**

```bash
cd frontend && npx tsc -b && npx vitest --run
```

- [ ] **Step 9 : Commit**

```
feat(transactions): E6 — bulk-categorize-filtered + checkbox sélectionner tous les résultats

Nouveau endpoint POST /api/transactions/bulk-categorize-filtered acceptant
un objet filter (mêmes critères que GET) sans limite de pagination.
Frontend : checkbox "Sélectionner les X résultats" dans la toolbar de
sélection. L'existant bulk-categorize (ids) est conservé intact.
Doc d'impact transactions.

Co-authored-by: Claude <noreply@anthropic.com>
```

---

## Task E7 — Toggle "afficher détails SEPA" sur Transactions

**Files :**
- Modify : `backend/app/schemas/transaction.py`
- Modify : `backend/app/api/transactions.py`
- Create : `backend/tests/test_e8_transaction_filters.py` (mutualisé avec E8)
- Modify : `frontend/src/components/TransactionFilters.tsx`
- Modify : `frontend/src/pages/TransactionsPage.tsx`
- Modify : `frontend/src/content/documentation.ts`

**Pourquoi :** Les transactions SEPA agrégées ont des enfants détaillés (`parent_transaction_id IS NOT NULL`). Actuellement, `list_transactions` filtre déjà `is_aggregation_parent = FALSE` mais n'exclut pas les enfants SEPA : les virements SEPA apparaissent donc dupliqués (parent agrégé + N enfants). Un toggle "Afficher les détails SEPA" permet d'explorer les sous-transactions tout en ayant une vue nette par défaut.

**Steps :**

- [ ] **Step 1 : Modifier TransactionFilter dans schemas/transaction.py**

Ajouter :

```python
include_sepa_children: bool = False
```

- [ ] **Step 2 : Modifier list_transactions dans transactions.py**

Après le filtre `is_aggregation_parent`, ajouter :

```python
if not filters.include_sepa_children:
    conditions.append(Transaction.parent_transaction_id.is_(None))
```

Remplacer l'existant `Transaction.is_aggregation_parent.is_(False)` qui est gardé (filtre les parents agrégés de haut niveau), le nouveau filtre exclut les enfants SEPA. Les deux filtres sont complémentaires.

- [ ] **Step 3 : Test (intégré dans test_e8_transaction_filters.py)**

Le test sera créé à l'étape E8 Step 1 avec des cas couvrant E7 et E8 ensemble.

- [ ] **Step 4 : Frontend — toggle dans TransactionFilters.tsx**

Dans `TransactionFilters.tsx`, ajouter un toggle checkbox après les filtres existants :

```tsx
<div className="flex items-center gap-2">
  <input
    type="checkbox"
    id="include-sepa"
    checked={filters.include_sepa_children ?? false}
    onChange={(e) => onChange({ ...filters, include_sepa_children: e.target.checked || undefined, page: 1 })}
    className="h-3.5 w-3.5 accent-ink"
  />
  <label htmlFor="include-sepa" className="text-[12.5px] text-ink-2 select-none cursor-pointer">
    Afficher les virements SEPA détaillés
  </label>
</div>
```

- [ ] **Step 5 : Documentation d'impact**

Dans la section `transactions`, ajouter dans `does` :

> "Par défaut, les virements SEPA apparaissent sous leur forme agrégée (une ligne par virement). Pour voir le détail de chaque sous-transaction : cochez 'Afficher les virements SEPA détaillés'. Cette vue expose les lignes enfants, utile pour comprendre la décomposition d'un virement de masse."

Ajouter une `FeatureDoc` pour `id: "toggle-sepa"`.

- [ ] **Step 6 : Commit (sera groupé avec E8)**

---

## Task E8 — Filtre amount_min/amount_max + persistance URL des filtres Transactions

**Files :**
- Modify : `backend/app/schemas/transaction.py` (mutualisé avec E7)
- Modify : `backend/app/api/transactions.py` (mutualisé avec E7)
- Create : `backend/tests/test_e8_transaction_filters.py`
- Modify : `frontend/src/components/TransactionFilters.tsx`
- Modify : `frontend/src/pages/TransactionsPage.tsx`
- Modify : `frontend/src/content/documentation.ts`

**Pourquoi :** Absence de filtre montant et perte des filtres au rechargement de page sont deux points de friction majeurs. La persistance URL permet aussi de partager un lien vers une vue filtrée.

**Steps :**

- [ ] **Step 1 : Test backend qui échoue**

Créer `backend/tests/test_e8_transaction_filters.py` :

```python
"""E7/E8 — Tests des nouveaux filtres transactions : SEPA enfants, amount_min/max."""
import pytest
from decimal import Decimal


def test_amount_min_filter(client, db_session, admin_auth_headers, bank_account_factory, transaction_factory, entity_factory):
    entity = entity_factory()
    ba = bank_account_factory(entity_id=entity.id)
    tx_small = transaction_factory(bank_account_id=ba.id, amount=Decimal("-10.00"))
    tx_large = transaction_factory(bank_account_id=ba.id, amount=Decimal("-500.00"))

    resp = client.get(f"/api/transactions?entity_id={entity.id}&amount_min=100", headers=admin_auth_headers)
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["items"]]
    assert tx_large.id in ids
    assert tx_small.id not in ids


def test_amount_max_filter(client, db_session, admin_auth_headers, bank_account_factory, transaction_factory, entity_factory):
    entity = entity_factory()
    ba = bank_account_factory(entity_id=entity.id)
    tx_small = transaction_factory(bank_account_id=ba.id, amount=Decimal("-10.00"))
    tx_large = transaction_factory(bank_account_id=ba.id, amount=Decimal("-500.00"))

    resp = client.get(f"/api/transactions?entity_id={entity.id}&amount_max=50", headers=admin_auth_headers)
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["items"]]
    assert tx_small.id in ids
    assert tx_large.id not in ids


def test_sepa_children_hidden_by_default(client, db_session, admin_auth_headers, bank_account_factory, transaction_factory, entity_factory):
    entity = entity_factory()
    ba = bank_account_factory(entity_id=entity.id)
    parent_tx = transaction_factory(bank_account_id=ba.id, parent_transaction_id=None)
    child_tx = transaction_factory(bank_account_id=ba.id, parent_transaction_id=parent_tx.id)

    resp = client.get(f"/api/transactions?entity_id={entity.id}", headers=admin_auth_headers)
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["items"]]
    assert child_tx.id not in ids

def test_sepa_children_visible_when_toggled(client, db_session, admin_auth_headers, bank_account_factory, transaction_factory, entity_factory):
    entity = entity_factory()
    ba = bank_account_factory(entity_id=entity.id)
    parent_tx = transaction_factory(bank_account_id=ba.id)
    child_tx = transaction_factory(bank_account_id=ba.id, parent_transaction_id=parent_tx.id)

    resp = client.get(f"/api/transactions?entity_id={entity.id}&include_sepa_children=true", headers=admin_auth_headers)
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["items"]]
    assert child_tx.id in ids
```

```bash
docker exec horizon-backend-1 pytest backend/tests/test_e8_transaction_filters.py -v
# Attendu : FAILED
```

- [ ] **Step 2 : Ajouter amount_min/amount_max dans TransactionFilter**

Dans `backend/app/schemas/transaction.py` (même fichier que E7), ajouter :

```python
from decimal import Decimal

class TransactionFilter(BaseModel):
    # … champs existants …
    amount_min: Decimal | None = None
    amount_max: Decimal | None = None
    include_sepa_children: bool = False  # ajouté en E7
```

- [ ] **Step 3 : Ajouter les filtres dans list_transactions**

Dans `backend/app/api/transactions.py`, après le filtre `uncategorized` :

```python
if filters.amount_min is not None:
    conditions.append(func.abs(Transaction.amount) >= filters.amount_min)
if filters.amount_max is not None:
    conditions.append(func.abs(Transaction.amount) <= filters.amount_max)
```

- [ ] **Step 4 : Test vert backend**

```bash
docker exec horizon-backend-1 pytest backend/tests/test_e8_transaction_filters.py -v
# Attendu : 4 passed
```

- [ ] **Step 5 : Frontend — inputs montant dans TransactionFilters.tsx**

Ajouter deux inputs numériques `Montant min (€)` / `Montant max (€)` après les filtres existants, avec `type="number"`, `min="0"`, `step="0.01"`. Ils envoient `amount_min` / `amount_max` dans l'objet `filters`.

- [ ] **Step 6 : Persistance URL avec useSearchParams**

Dans `frontend/src/pages/TransactionsPage.tsx` :

1. Remplacer `useState<TransactionFilter>` par une synchronisation avec `useSearchParams` de react-router-dom :

```typescript
import { useSearchParams } from "react-router-dom";

function filtersFromSearchParams(sp: URLSearchParams): TransactionFilter {
  return {
    page: Number(sp.get("page") ?? 1),
    per_page: Number(sp.get("per_page") ?? 50),
    search: sp.get("search") ?? undefined,
    bank_account_id: sp.has("account") ? Number(sp.get("account")) : undefined,
    uncategorized: sp.get("uncategorized") === "true" || undefined,
    category_id: sp.has("category") ? Number(sp.get("category")) : undefined,
    amount_min: sp.has("amount_min") ? parseDecimalParam(sp.get("amount_min")!) : undefined,
    amount_max: sp.has("amount_max") ? parseDecimalParam(sp.get("amount_max")!) : undefined,
    include_sepa_children: sp.get("sepa") === "true",
    date_from: sp.get("date_from") ?? undefined,
    date_to: sp.get("date_to") ?? undefined,
    counterparty_id: sp.has("counterparty") ? Number(sp.get("counterparty")) : undefined,
  };
}

function filtersToSearchParams(f: TransactionFilter): URLSearchParams {
  const sp = new URLSearchParams();
  if (f.page && f.page > 1) sp.set("page", String(f.page));
  if (f.search) sp.set("search", f.search);
  if (f.bank_account_id) sp.set("account", String(f.bank_account_id));
  if (f.uncategorized) sp.set("uncategorized", "true");
  if (f.category_id) sp.set("category", String(f.category_id));
  if (f.amount_min) sp.set("amount_min", String(f.amount_min));
  if (f.amount_max) sp.set("amount_max", String(f.amount_max));
  if (f.include_sepa_children) sp.set("sepa", "true");
  if (f.date_from) sp.set("date_from", String(f.date_from));
  if (f.date_to) sp.set("date_to", String(f.date_to));
  if (f.counterparty_id) sp.set("counterparty", String(f.counterparty_id));
  return sp;
}

// Dans le composant :
const [searchParams, setSearchParams] = useSearchParams();
const filters = filtersFromSearchParams(searchParams);

function setFilters(next: TransactionFilter) {
  setSearchParams(filtersToSearchParams(next), { replace: true });
}
```

2. Remplacer toutes les occurrences de `setFilters({ ...filters, … })` par la même signature (l'API ne change pas pour les appelants internes).

3. Conserver `selectedIds` en `useState` local (pas dans l'URL — trop volatile).

- [ ] **Step 7 : Documentation d'impact**

Dans la section `transactions`, ajouter dans `tips` :

> "Les filtres actifs sont mémorisés dans l'URL de la page. Vous pouvez copier-coller l'URL pour partager une vue filtrée avec un collègue ou retrouver votre contexte après un rechargement."
> "Les filtres Montant min et Montant max s'appliquent sur la valeur absolue du montant (crédit ou débit). Un filtre 'Montant min = 1000' isole toutes les opérations de plus de 1 000 €, quel que soit le sens."

Ajouter des `FeatureDoc` pour `id: "filtres-montant"` et `id: "url-persistence-transactions"`.

- [ ] **Step 8 : TypeScript + Vitest**

```bash
cd frontend && npx tsc -b && npx vitest --run
```

- [ ] **Step 9 : Commit (commiter E7 + E8 ensemble)**

```
feat(transactions): E7/E8 — toggle SEPA, filtres montant, persistance URL des filtres

E7 : filtre include_sepa_children (défaut false — enfants masqués), toggle UI
dans TransactionFilters.
E8 : filtres amount_min/amount_max (valeur absolue), synchronisation de tous
les filtres avec useSearchParams (rafraîchissement préserve l'état, URL
partageable). Doc d'impact transactions.

Co-authored-by: Claude <noreply@anthropic.com>
```

---

## Task E9 — Hit count par règle exposé dans la liste

**Files :**
- Modify : `backend/app/api/rules.py`
- Modify : `backend/app/schemas/categorization_rule.py`
- Create : `backend/tests/test_e9_rules_hit_count.py`
- Modify : `frontend/src/api/rules.ts`
- Modify : `frontend/src/components/SortableRulesTable.tsx`
- Modify : `frontend/src/pages/RulesPage.tsx`
- Modify : `frontend/src/content/documentation.ts`

**Pourquoi :** Sans hit count, il est impossible de savoir quelles règles sont actives et lesquelles ne matchent jamais. Afficher le nombre de transactions catégorisées par chaque règle aide à détecter les règles obsolètes et à prioriser les ajustements. Calcul live via COUNT retenu (table < 50k lignes, cohérence garantie, pas de compteur à maintenir).

**Steps :**

- [ ] **Step 1 : Test backend qui échoue**

Créer `backend/tests/test_e9_rules_hit_count.py` :

```python
"""E9 — GET /api/rules retourne un champ hit_count par règle."""
import pytest
from app.models.categorization_rule import CategorizationRule
from app.models.transaction import Transaction, TransactionCategorizationSource


def test_rules_list_includes_hit_count(
    client, db_session, admin_auth_headers, category_factory,
    bank_account_factory, transaction_factory
):
    cat = category_factory(name="Hit Count Test")
    rule = CategorizationRule(
        name="HitCountTestRule", priority=9990, is_system=False,
        label_operator="CONTAINS", label_value="HITCOUNT",
        direction="ANY", category_id=cat.id,
    )
    db_session.add(rule)
    db_session.flush()

    ba = bank_account_factory()
    for i in range(3):
        tx = transaction_factory(bank_account_id=ba.id, label=f"HITCOUNT TX {i}")
        tx.categorization_rule_id = rule.id
        tx.category_id = cat.id
        tx.categorized_by = TransactionCategorizationSource.RULE
    db_session.commit()

    resp = client.get("/api/rules?scope=all", headers=admin_auth_headers)
    assert resp.status_code == 200
    rules = resp.json()
    hit_rule = next((r for r in rules if r["name"] == "HitCountTestRule"), None)
    assert hit_rule is not None
    assert hit_rule["hit_count"] == 3


def test_rules_with_zero_hits(client, db_session, admin_auth_headers, category_factory):
    cat = category_factory(name="Zero Hits")
    rule = CategorizationRule(
        name="ZeroHitRule", priority=9991, is_system=False,
        label_operator="CONTAINS", label_value="ZEROHIT",
        direction="ANY", category_id=cat.id,
    )
    db_session.add(rule)
    db_session.commit()

    resp = client.get("/api/rules?scope=all", headers=admin_auth_headers)
    rules = resp.json()
    zero_rule = next((r for r in rules if r["name"] == "ZeroHitRule"), None)
    assert zero_rule is not None
    assert zero_rule["hit_count"] == 0
```

```bash
docker exec horizon-backend-1 pytest backend/tests/test_e9_rules_hit_count.py -v
# Attendu : FAILED (champ hit_count absent du schéma)
```

- [ ] **Step 2 : Modifier RuleRead dans les schémas**

Dans `backend/app/schemas/categorization_rule.py`, dans la classe `RuleRead`, ajouter :

```python
hit_count: int = 0
```

- [ ] **Step 3 : Modifier GET /api/rules pour calculer hit_count**

Dans `backend/app/api/rules.py`, modifier `list_rules` pour joindre un COUNT :

```python
from sqlalchemy import func as sqlfunc, literal

@router.get("", response_model=list[RuleRead])
def list_rules(
    # … paramètres existants …
) -> list[RuleRead]:
    # Sous-requête hit count
    hit_count_sq = (
        select(
            Transaction.categorization_rule_id,
            sqlfunc.count(Transaction.id).label("cnt"),
        )
        .where(Transaction.categorization_rule_id.isnot(None))
        .group_by(Transaction.categorization_rule_id)
        .subquery()
    )

    q = (
        select(
            CategorizationRule,
            sqlfunc.coalesce(hit_count_sq.c.cnt, 0).label("hit_count"),
        )
        .outerjoin(hit_count_sq, hit_count_sq.c.categorization_rule_id == CategorizationRule.id)
    )

    # … filtres existants sur q …

    q = q.order_by(
        CategorizationRule.entity_id.asc().nulls_last(),
        CategorizationRule.priority.asc(),
    ).limit(limit).offset(offset)

    rows = session.execute(q).all()
    result = []
    for rule, hit_count in rows:
        rd = RuleRead.model_validate(rule)
        rd.hit_count = hit_count
        result.append(rd)
    return result
```

Note : `RuleRead` doit être validé depuis l'ORM (`model_validate(rule)`) puis le champ `hit_count` est injecté manuellement car il n'est pas une colonne du modèle.

- [ ] **Step 4 : Test vert backend**

```bash
docker exec horizon-backend-1 pytest backend/tests/test_e9_rules_hit_count.py -v
# Attendu : 2 passed
```

- [ ] **Step 5 : Frontend — RuleRead enrichi + colonne Hits**

Dans `frontend/src/api/rules.ts`, enrichir l'interface `Rule` :

```typescript
export interface Rule {
  // … champs existants …
  hit_count: number;
}
```

Dans `frontend/src/components/SortableRulesTable.tsx` :

1. Ajouter `hit_count` dans la prop de tri :

```typescript
interface Props {
  // … existant …
  sortByHits?: boolean;
  onSortByHits?: () => void;
}
```

2. Ajouter la colonne dans le `<thead>` entre Conditions et Catégorie :

```tsx
<th
  className="cursor-pointer px-3 py-2.5 text-left text-[11.5px] font-semibold uppercase tracking-wider text-muted-foreground hover:text-ink"
  onClick={onSortByHits}
  title="Trier par nombre de transactions catégorisées par cette règle"
>
  Hits {sortByHits ? "▼" : ""}
</th>
```

3. Ajouter la cellule dans `SortableRow` :

```tsx
<td className="px-3 py-3 text-center font-mono tabular-nums text-[12.5px] text-ink-2">
  {rule.hit_count ?? 0}
</td>
```

Dans `frontend/src/pages/RulesPage.tsx` :

```typescript
const [sortByHits, setSortByHits] = useState(false);

const sortedRules = useMemo(() => {
  if (!sortByHits) return filteredRules;
  return [...filteredRules].sort((a, b) => (b.hit_count ?? 0) - (a.hit_count ?? 0));
}, [filteredRules, sortByHits]);
```

Passer `sortByHits` et `onSortByHits={() => setSortByHits((v) => !v)}` à `<SortableRulesTable>`.

- [ ] **Step 6 : Documentation d'impact**

Dans `documentation.ts`, section `regles`, dans `sees`, ajouter :

> "Une colonne Hits entre Conditions et Catégorie : nombre de transactions que cette règle a catégorisées. Un clic sur l'en-tête trie les règles du plus au moins utilisé."

Ajouter une `FeatureDoc` pour `id: "rules-hit-count"`.

- [ ] **Step 7 : TypeScript + Vitest**

```bash
cd frontend && npx tsc -b && npx vitest --run
```

- [ ] **Step 8 : Commit**

```
feat(rules): E9 — colonne Hits (hit_count) dans la liste des règles

Calcul live via COUNT(transactions.categorization_rule_id) jointuré dans
GET /api/rules. Colonne Hits dans SortableRulesTable avec tri cliquable.
RuleRead enrichi de hit_count. Doc d'impact section regles.

Co-authored-by: Claude <noreply@anthropic.com>
```

---

## Task E10 — Afficher window_month dans header AnalysePage (bonus)

**Files :**
- Modify : `frontend/src/types/analysis.ts`
- Modify : `frontend/src/components/analyse/TopMoversCard.tsx`

**Pourquoi :** Le backend renvoie déjà `window_month: str | None` dans `TopMoversResponse` (cf. `backend/app/schemas/analysis.py:111`). Le frontend ignore ce champ (absent de `types/analysis.ts`). L'afficher dans le sous-titre de `TopMoversCard` informe l'utilisateur sur quelle période la comparaison est calculée.

**Steps :**

- [ ] **Step 1 : Ajouter window_month dans l'interface TS**

Dans `frontend/src/types/analysis.ts`, compléter `TopMoversResponse` :

```typescript
export interface TopMoversResponse {
  increases: TopMoverRow[];
  decreases: TopMoverRow[];
  window_month?: string | null;  // "YYYY-MM" du mois courant utilisé comme ancre
}
```

- [ ] **Step 2 : Afficher dans TopMoversCard.tsx**

Dans `TopMoversCardInner`, remplacer le sous-titre statique :

```tsx
<div className="mt-0.5 text-[12.5px] text-muted-foreground">
  Variations les plus fortes vs mois précédent
  {query.data?.window_month && (
    <span className="ml-1 font-mono text-[11px]">
      ({formatWindowMonth(query.data.window_month)})
    </span>
  )}
</div>
```

Ajouter la fonction utilitaire :

```typescript
function formatWindowMonth(ym: string): string {
  // "2026-04" → "avr. 2026"
  const [year, month] = ym.split("-");
  return new Date(Number(year), Number(month) - 1, 1).toLocaleDateString("fr-FR", {
    month: "short",
    year: "numeric",
  });
}
```

- [ ] **Step 3 : TypeScript**

```bash
cd frontend && npx tsc -b
```

- [ ] **Step 4 : Commit**

```
fix(analyse): E10 — afficher window_month dans TopMoversCard

Le backend renvoyait déjà window_month dans TopMoversResponse mais le
frontend ne le déclarait pas dans l'interface TS. Corrigé + affichage
dans le sous-titre de la carte.

Co-authored-by: Claude <noreply@anthropic.com>
```

---

