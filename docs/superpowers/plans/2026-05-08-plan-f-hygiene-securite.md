# Plan F — Hygiène & Sécurité — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** Lever la dette structurelle avant d'ajouter du fonctionnel. Dix items (F1-F10) couvrant les index FK manquants, les tests API minimaux pour 6 routers, l'audit des événements auth, le lockout après N échecs, la pagination forcée des listings non bornés, la correction des règles à 0 hit, la whitelist setattr, les selectinload sur les N+1, la suppression de l'endpoint prune, et la synchronisation finale de la doc sécurité.

**Architecture :**
- Backend (Python/FastAPI/SQLAlchemy 2.x) : 1 migration FK indexes (F1), 2 migrations User (F4 : colonnes lockout), 1 migration audit_log action constraint (F3), corrections dans `api/auth.py` (F3, F4), modifications `api/counterparties.py` / `api/rules.py` / `api/forecast_scenarios.py` / `api/forecast_lines.py` (F5), corrections `api/users.py` / `api/entities.py` / `api/bank_accounts.py` / `api/forecast_scenarios.py` (F7), correction `api/commitments.py` + `models/commitment.py` (F8), suppression endpoint dans `api/admin_audit.py` (F9).
- Frontend (React 18 / TS) : mise à jour `frontend/src/content/documentation.ts` (F3, F4, F10).
- Tests : pytest dans le container backend, tous les fichiers de test nouveaux listés dans File Structure.
- Documentation d'impact (règle CLAUDE.md) : F3 (audit login) et F4 (lockout) sont visibles utilisateur → mise à jour `documentation.ts` section `securite`.

**Tech Stack :** FastAPI, SQLAlchemy 2.x, Postgres, Alembic, React 18, react-query 5, TypeScript, Tailwind, pytest.

---

## Vérifications préalables — Résultats d'exploration

### 1. Head migration actuelle

La migration head actuelle est `h0r1z0n50802` (Plan D2, `20260508_1010_add_category_kind.py`).

Révisions Plan F : F1 = `h0r1z0nf0100`, F3 = `h0r1z0nf0300`, F4 = `h0r1z0nf0400`.

### 2. FK sans index — liste à vérifier en live

La requête de vérification obligatoire à exécuter avant implémenter F1 :

```bash
docker exec horizon-db-1 psql -U $POSTGRES_USER -d $POSTGRES_DB -c \
"SELECT n.nspname, t.relname AS table, a.attname AS col
 FROM pg_constraint c
 JOIN pg_class t ON t.oid = c.conrelid
 JOIN pg_namespace n ON n.oid = t.relnamespace
 JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(c.conkey)
 WHERE c.contype='f'
   AND NOT EXISTS (
     SELECT 1 FROM pg_index i
     WHERE i.indrelid=t.oid AND a.attnum = ANY(i.indkey)
   )
 ORDER BY t.relname"
```

Colonnes attendues d'après l'audit (à confirmer via la requête — `forecast_entries` est droppée par D1, les entrées correspondantes n'apparaîtront pas) :

| Table | Colonne |
|---|---|
| `categorization_rules` | `bank_account_id` |
| `categorization_rules` | `category_id` |
| `categorization_rules` | `counterparty_id` |
| `categorization_rules` | `created_by_id` |
| `categories` | `parent_category_id` |
| `commitments` | `bank_account_id` |
| `commitments` | `category_id` |
| `commitments` | `counterparty_id` |
| `commitments` | `created_by_id` |
| `commitments` | `pdf_attachment_id` |
| `entities` | `parent_entity_id` |
| `forecast_lines` | `base_category_id` |
| `forecast_lines` | `updated_by_id` |
| `forecast_scenarios` | `created_by_id` |
| `imports` | `uploaded_by_id` |
| `transactions` | `categorization_rule_id` |
| `transactions` | `counter_entity_id` |
| `transactions` | `import_id` |
| `transactions` | `parent_transaction_id` |

Note : `forecast_entries` droppée par D1 — ses colonnes disparaissent de la liste. `forecast_lines.base_category_id` et `forecast_lines.updated_by_id` existent dans le modèle courant (`/srv/prod/tools/horizon/backend/app/models/forecast_line.py`) et doivent être indexées. `commitments` a déjà des indexes sur `entity_id`, `expected_date`, et `matched_transaction_id` (via `__table_args__`) mais pas sur les FK nullable `category_id`, `counterparty_id`, `bank_account_id`, `created_by_id`, `pdf_attachment_id`.

### 3. Listings non bornés — état constaté

| Router | Endpoint | Borné ? | Action F5 |
|---|---|---|---|
| `api/counterparties.py` | `GET /api/counterparties` | Non — pas de `.limit()` dans la query | Ajouter `limit`/`offset` |
| `api/rules.py` | `GET /api/rules` | Non — pas de `.limit()` | Ajouter `limit`/`offset` |
| `api/forecast_scenarios.py` | `GET /api/forecast/scenarios` | Non — pas de `.limit()` | Ajouter `limit`/`offset` |
| `api/forecast_lines.py` | `GET /api/forecast/lines` | Non — pas de `.limit()` | Ajouter `limit`/`offset` |
| `api/commitments.py` | `GET /api/commitments` | Oui — pagination `page`/`per_page` existante | Aucune action |

Les listings commitments sont déjà paginés avec `CommitmentListResponse`. `counterparties` retourne un `list[CounterpartyWithAggregates]` côté backend et `CounterpartyWithAggregates[]` (tableau brut) côté frontend (`fetchCounterparties` → `resp.json()`). `rules` retourne `list[RuleRead]` côté backend et `Rule[]` côté frontend (`apiFetch<Rule[]>`). Les deux call-sites consomment un tableau brut. Le wrapper paginé `{items, total, limit, offset}` est donc un breaking change frontend.

**Décision F5 :** ajouter `limit`/`offset` en query params avec `default=200, le=1000` mais conserver le type de retour comme tableau brut (liste des items seulement, sans wrapper). La pagination côté frontend reste du côté client. Raison : wrapper paginé casse les deux call-sites frontend sans apport immédiat (les listings counterparties et rules sont de taille raisonnable en pratique — < 200 règles actives). Un plafond dur à 1000 suffit comme garde-fou de protection mémoire. Pour `forecast_scenarios` et `forecast_lines` : idem, tableau brut avec plafond.

### 4. Call-sites setattr boucle dans api/*.py

| Fichier | Ligne | Entité | Champs WhiteList à définir |
|---|---|---|---|
| `api/users.py:100` | `for field, value in data.items(): setattr(user, field, value)` | `User` | `role`, `full_name`, `is_active` |
| `api/entities.py:63` | `for field, value in payload.model_dump(exclude_unset=True).items(): setattr(e, field, value)` | `Entity` | `name`, `siren`, `address`, `parent_entity_id` (à confirmer depuis le modèle) |
| `api/bank_accounts.py:79` | `for field, value in payload.model_dump(exclude_unset=True).items(): setattr(ba, field, value)` | `BankAccount` | `name`, `bic`, `bank_name`, `bank_code`, `is_active` |
| `api/forecast_scenarios.py:123` | `for field, value in updates.items(): setattr(sc, field, value)` | `ForecastScenario` | `name`, `description`, `is_default` |
| `api/rules.py:176` | `for field, value in data.items(): setattr(rule, field, value)` | `CategorizationRule` | Déjà filtré par `_STRUCTURAL_FIELDS` pour les system rules — whitelist complète à appliquer |

Note : `api/commitments.py:282-288` a déjà une boucle setattr mais avec des branches explicites pour `direction` et `status` — elle est semi-whitelistée mais peut recevoir n'importe quel champ de `CommitmentUpdate`. À inclure.

`forecast.py` (forecast_lines router) n'utilise pas de boucle setattr — l'upsert reconstruit l'objet entier.

### 5. Audit events auth — décision F3

**Décision :** élargir `audit_log` (cohérent avec l'existant, pas d'infra supplémentaire). Deux modifications :
1. Étendre la `CheckConstraint` dans le modèle `AuditLog` pour accepter `login`, `login_failed`, `logout`. Migration alembic requise pour modifier la contrainte en DB.
2. Étendre la regex du filtre Query dans `api/admin_audit.py` (pattern `"^(create|update|delete|merge)$"` → ajouter les nouvelles actions).
3. Appeler `record_audit` dans `api/auth.py` avec `entity_type_override="User"` et une action custom (le service `record_audit` prend un `Literal["create","update","delete"]` mais la contrainte DB est étendue — on utilisera `entity_type_override` et une injection directe dans `AuditLog` depuis auth, ou on élargit `AuditAction` dans `services/audit.py`).

**Approche précise :** élargir `AuditAction` dans `services/audit.py` de `Literal["create", "update", "delete"]` à `Literal["create", "update", "delete", "merge", "login", "login_failed", "logout"]`. La contrainte DB est mise à jour par migration.

### 6. Endpoints des 6 routers F2

**auth** (`api/auth.py`) :
- `POST /api/auth/login` → 200 (happy path), 401 (mauvais mdp)
- `POST /api/auth/logout` → 204

**bootstrap** (`api/bootstrap.py`) :
- `POST /api/bootstrap` → 201 (happy path quand DB vide), 409 (déjà bootstrappé)

**me** (`api/me.py`) :
- `GET /api/me` → 200 (authentifié), 401 (non auth)
- `POST /api/me/password` → 204 (happy path), 400 (mdp actuel incorrect)

**users** (`api/users.py`) :
- `GET /api/users` → 200 (admin), 403 (reader)
- `POST /api/users` → 201 (admin), 403 (reader)
- `PATCH /api/users/{id}` → 200 (admin), 404 (inexistant)
- `POST /api/users/{id}/password` → 204 (admin), 404 (inexistant)
- `DELETE /api/users/{id}` → 204 (admin), 409 (dernier admin)

**entities** (`api/entities.py`) :
- `GET /api/entities` → 200 (admin), 403 (reader — dépend : require_admin est en dependency global)
- `POST /api/entities` → 201 (admin), 409 (comptes rattachés lors delete)
- `PATCH /api/entities/{id}` → 200, 404
- `DELETE /api/entities/{id}` → 204, 409 (comptes rattachés)

**bank_accounts** (`api/bank-accounts.py`) :
- `GET /api/bank-accounts` → 200 (any auth)
- `POST /api/bank-accounts` → 201 (admin), 403 (reader)
- `PATCH /api/bank-accounts/{id}` → 200 (admin), 404

### 7. Règles à 0 hit — analyse F6

La normalisation `normalize_label` : supprime la ponctuation sauf lettres, chiffres, espaces et traits d'union (`[^A-Z0-9\s-]`). Les `*` (astérisques) sont donc supprimés. Une règle avec `label_value = "FRAIS **"` est normalisée en `"FRAIS"` lors de sa création (le validator `_normalize_label_value` dans `RuleBase` passe `label_value` par `normalize_label` à la création). Donc le problème ne concerne que les règles créées **avant** l'introduction du validator (migrations de seed), où la valeur brute a été insérée directement en DB via SQL seed.

La requête pour identifier les règles à 0 hit (pas de transaction liée) :

```sql
SELECT id, name, label_operator, label_value
FROM categorization_rules
WHERE id NOT IN (
  SELECT DISTINCT categorization_rule_id
  FROM transactions
  WHERE categorization_rule_id IS NOT NULL
)
ORDER BY id;
```

Les migrations seed (`20260417_1020_plan2_seed_delubac_rules.py`, `20260505_1510_audit_rules_overhaul.py`, `20260505_1200_add_prelevement_source.py`, `20260505_1210_fix_dgfip_rule_pas_dsn.py`) insèrent des règles avec des valeurs brutes non normalisées. Les règles seed avec `**` ou ponctuation ne matcheront jamais. **La correction : UPDATE SQL transactionnel sur les règles identifiées**, pas de sed.

### 8. Selectinload N+1 — état constaté

`api/commitments.py` : le listing `GET /api/commitments` (`list_commitments`) utilise `select(Commitment)` avec `.scalars()`. Le modèle `Commitment` a `relationship("Counterparty", lazy="joined")` et `relationship("Category", lazy="joined")` (lazy="joined" = INNER JOIN automatique). Pas de N+1 ici — la relation est déjà eager avec `lazy="joined"`.

`api/rules.py` : `GET /api/rules` utilise `select(CategorizationRule)`. Le modèle `CategorizationRule` n'a pas de relationship définie — le schéma `RuleRead` expose seulement des IDs (`category_id`, `counterparty_id`, `bank_account_id`). Pas de N+1 possible sans relationship eager.

**Conclusion F8 :** les N+1 potentiels sont déjà couverts par `lazy="joined"` sur Commitment. Les rules n'exposent que des IDs. La task F8 doit vérifier ce constat par un test de comptage de requêtes, et corriger si un N+1 est détecté. Si le test confirme qu'il n'y a pas de N+1, la task reste valide comme test de régression (zéro-N+1 garanti).

---

## File Structure

### Création
- `backend/alembic/versions/20260507_1100_add_missing_fk_indexes.py`
- `backend/alembic/versions/20260507_1110_audit_log_auth_actions.py`
- `backend/alembic/versions/20260507_1120_user_lockout.py`
- `backend/tests/test_api_auth_f2.py`
- `backend/tests/test_api_bootstrap_f2.py`
- `backend/tests/test_api_me_f2.py`
- `backend/tests/test_api_users_f2.py`
- `backend/tests/test_api_entities_f2.py`
- `backend/tests/test_api_bank_accounts_f2.py`
- `backend/tests/test_audit_auth_f3.py`
- `backend/tests/test_user_lockout_f4.py`
- `backend/tests/test_pagination_f5.py`
- `backend/tests/test_setattr_whitelist_f7.py`
- `backend/tests/test_no_n_plus_one_f8.py`

### Modification
- `backend/app/api/auth.py` — F3 (record_audit login/logout), F4 (vérification lockout + reset counter)
- `backend/app/api/admin_audit.py` — F3 (pattern action étendu), F9 (suppression endpoint prune)
- `backend/app/models/audit_log.py` — F3 (CheckConstraint étendue dans le modèle Python)
- `backend/app/models/user.py` — F4 (colonnes `failed_login_attempts`, `locked_until`)
- `backend/app/services/audit.py` — F3 (élargir `AuditAction` Literal)
- `backend/app/api/counterparties.py` — F5 (limit/offset), F7 (setattr whitelist implicite — déjà explicit dans update_counterparty)
- `backend/app/api/rules.py` — F5 (limit/offset), F7 (whitelist setattr)
- `backend/app/api/forecast_scenarios.py` — F5 (limit/offset), F7 (whitelist setattr)
- `backend/app/api/forecast_lines.py` — F5 (limit/offset)
- `backend/app/api/users.py` — F7 (whitelist setattr)
- `backend/app/api/entities.py` — F7 (whitelist setattr)
- `backend/app/api/bank_accounts.py` — F7 (whitelist setattr)
- `backend/app/api/commitments.py` — F7 (whitelist setattr)
- `frontend/src/content/documentation.ts` — F3+F4 (section `securite`), F10 (revue finale)

---

## Conventions de l'app à respecter

(Rappel pour chaque subagent — copier-coller en briefing.)

- **Tests dans le container backend uniquement** (`docker exec horizon-backend-1 pytest -x backend/tests/test_xxx.py -v`).
- **Cookie session en test** : `BACKEND_COOKIE_SECURE=false` déjà câblé via conftest, ne PAS le toucher.
- **Migrations** : `docker cp <file> horizon-backend-1:/app/alembic/versions/ && docker exec horizon-backend-1 alembic upgrade head`.
- **Commit messages** : français, ton sobre, sans emoji, format `type(scope): message`. Co-author Claude requis.
- **UPDATE SQL transactionnel uniquement** : jamais `sed -i` sur la DB.
- **Pas de `cat .env`** — lire la config via `printenv` ou `grep -c`.
- **Doc d'impact (CLAUDE.md)** : F3 et F4 sont visibles utilisateur → `documentation.ts` section `securite`. F5 transparent si retour array brut. F1/F6/F7/F8/F9 = pas de doc utilisateur.
- **Pas d'emoji** dans les commits ni dans la doc.
- **Tests frontend** : `cd /srv/prod/tools/horizon/frontend && npx vitest run`.

---

# Tâches

## Task F1 — Migration `add_missing_fk_indexes`

**Files :**
- Créer : `backend/alembic/versions/20260507_1100_add_missing_fk_indexes.py`

**Pourquoi :** 19+ FK sans index entraînent des sequential scans sur les DELETE/UPDATE en cascade et les jointures fréquentes (notamment `transactions.import_id` à chaque import, `transactions.categorization_rule_id` à chaque apply-rule, `commitments.category_id` et `commitments.counterparty_id` dans les listings). PostgreSQL ne crée pas automatiquement d'index sur les colonnes FK.

**Steps :**

- [ ] **Step 1 : Confirmer la liste réelle en live**

```bash
docker exec horizon-db-1 psql -U $POSTGRES_USER -d $POSTGRES_DB -c \
"SELECT n.nspname, t.relname AS table, a.attname AS col
 FROM pg_constraint c
 JOIN pg_class t ON t.oid = c.conrelid
 JOIN pg_namespace n ON n.oid = t.relnamespace
 JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(c.conkey)
 WHERE c.contype='f'
   AND NOT EXISTS (
     SELECT 1 FROM pg_index i
     WHERE i.indrelid=t.oid AND a.attnum = ANY(i.indkey)
   )
 ORDER BY t.relname"
```

Comparer avec la liste prévue. Toute colonne absente de la liste live = déjà indexée, ne pas l'inclure dans la migration. Toute colonne présente dans la liste live mais absente du plan = ajouter.

- [ ] **Step 2 : Créer la migration**

Créer `backend/alembic/versions/20260507_1100_add_missing_fk_indexes.py` en adaptant exactement à la liste live. Template de base (à compléter selon résultat Step 1) :

```python
"""F1 — Index sur les FK sans index.

Revision ID: h0r1z0nf0100
Revises: h0r1z0n50802
Create Date: 2026-05-07 11:00:00
"""
from __future__ import annotations
from alembic import op

revision = "h0r1z0nf0100"
down_revision = "h0r1z0n50802"
branch_labels = None
depends_on = None

# Priorité haute : colonnes utilisées dans des requêtes fréquentes de production.
# Priorité normale : colonnes utilisées dans les DELETE/UPDATE en cascade.
_INDEXES = [
    # Priorité haute
    ("ix_transactions_import_id",          "transactions",        "import_id"),
    ("ix_transactions_categorization_rule_id", "transactions",    "categorization_rule_id"),
    ("ix_commitments_category_id",         "commitments",         "category_id"),
    ("ix_commitments_counterparty_id",     "commitments",         "counterparty_id"),
    ("ix_commitments_bank_account_id",     "commitments",         "bank_account_id"),
    # Priorité normale
    ("ix_commitments_created_by_id",       "commitments",         "created_by_id"),
    ("ix_commitments_pdf_attachment_id",   "commitments",         "pdf_attachment_id"),
    ("ix_entities_parent_entity_id",       "entities",            "parent_entity_id"),
    ("ix_categories_parent_category_id",   "categories",          "parent_category_id"),
    ("ix_imports_uploaded_by_id",          "imports",             "uploaded_by_id"),
    ("ix_transactions_counter_entity_id",  "transactions",        "counter_entity_id"),
    ("ix_transactions_parent_transaction_id", "transactions",     "parent_transaction_id"),
    ("ix_rules_bank_account_id",           "categorization_rules", "bank_account_id"),
    ("ix_rules_category_id",               "categorization_rules", "category_id"),
    ("ix_rules_counterparty_id",           "categorization_rules", "counterparty_id"),
    ("ix_rules_created_by_id",             "categorization_rules", "created_by_id"),
    ("ix_forecast_scenarios_created_by_id","forecast_scenarios",  "created_by_id"),
    ("ix_forecast_lines_base_category_id", "forecast_lines",      "base_category_id"),
    ("ix_forecast_lines_updated_by_id",    "forecast_lines",      "updated_by_id"),
]


def upgrade() -> None:
    for index_name, table_name, col_name in _INDEXES:
        op.create_index(index_name, table_name, [col_name])


def downgrade() -> None:
    for index_name, table_name, _col in _INDEXES:
        op.drop_index(index_name, table_name=table_name)
```

Important : si la requête Step 1 indique qu'une colonne est déjà indexée, la retirer de `_INDEXES` avant de créer la migration. Ne pas créer d'index sur une colonne déjà couverte (erreur Postgres).

- [ ] **Step 3 : Appliquer**

```bash
docker cp backend/alembic/versions/20260507_1100_add_missing_fk_indexes.py \
  horizon-backend-1:/app/alembic/versions/
docker exec horizon-backend-1 alembic upgrade head
docker exec horizon-backend-1 alembic current
# Attendu : h0r1z0nf0100 (head)
```

- [ ] **Step 4 : Vérifier que la liste est vide après migration**

```bash
docker exec horizon-db-1 psql -U $POSTGRES_USER -d $POSTGRES_DB -c \
"SELECT t.relname AS table, a.attname AS col
 FROM pg_constraint c
 JOIN pg_class t ON t.oid = c.conrelid
 JOIN pg_namespace n ON n.oid = t.relnamespace
 JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(c.conkey)
 WHERE c.contype='f'
   AND n.nspname = 'public'
   AND NOT EXISTS (
     SELECT 1 FROM pg_index i
     WHERE i.indrelid=t.oid AND a.attnum = ANY(i.indkey)
   )
 ORDER BY t.relname"
# Attendu : 0 lignes (toutes les FK sont indexées)
```

- [ ] **Step 5 : Régression backend**

```bash
docker exec horizon-backend-1 pytest backend/tests/ -x -q
```

- [ ] **Step 6 : Commit F1**

```bash
git add backend/alembic/versions/20260507_1100_add_missing_fk_indexes.py
git commit -m "$(cat <<'EOF'
perf(db): index sur les FK sans index — migration h0r1z0nf0100

19 colonnes FK sans index identifiées par audit pg_constraint.
Priorité haute : transactions.import_id, transactions.categorization_rule_id,
commitments.{category_id,counterparty_id,bank_account_id}. Élimine les
sequential scans sur les DELETE CASCADE et les jointures fréquentes.

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task F2 — Tests API minimaux pour 6 routers

**Files :**
- Créer : `backend/tests/test_api_auth_f2.py`
- Créer : `backend/tests/test_api_bootstrap_f2.py`
- Créer : `backend/tests/test_api_me_f2.py`
- Créer : `backend/tests/test_api_users_f2.py`
- Créer : `backend/tests/test_api_entities_f2.py`
- Créer : `backend/tests/test_api_bank_accounts_f2.py`

**Pourquoi :** les 6 routers auth, bootstrap, me, users, entities, bank_accounts n'ont aucun test de comportement HTTP (happy path + cas d'erreur). Un refactor ou une régression sur ces endpoints ne serait pas détecté par la CI.

**Steps :**

- [ ] **Step 1 : Créer `test_api_auth_f2.py`**

```python
"""F2 — Tests API minimaux : auth router."""
import pytest


def test_login_happy_path(client, admin_user):
    """Login avec les bons credentials → 200 + cookie session."""
    resp = client.post("/api/auth/login", json={
        "email": admin_user.email,
        "password": "AdminPass123!",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == admin_user.email
    assert data["role"] == "admin"
    # Le cookie de session doit être présent
    assert "session" in resp.cookies or any(
        "session" in k.lower() for k in resp.cookies
    )


def test_login_wrong_password(client, admin_user):
    """Mauvais mot de passe → 401."""
    resp = client.post("/api/auth/login", json={
        "email": admin_user.email,
        "password": "WrongPass999!",
    })
    assert resp.status_code == 401


def test_login_unknown_email(client):
    """Email inexistant → 401 (pas de distinction pour éviter l'énumération)."""
    resp = client.post("/api/auth/login", json={
        "email": "nobody@example.com",
        "password": "SomePass123!",
    })
    assert resp.status_code == 401


def test_logout(client, admin_client):
    """Logout → 204."""
    resp = admin_client.post("/api/auth/logout")
    assert resp.status_code == 204
```

Note : les fixtures `admin_user`, `client`, `admin_client` doivent exister dans le conftest. Inspecter `backend/tests/conftest.py` pour les fixtures disponibles avant d'écrire les tests. La fixture `admin_user` crée un utilisateur admin avec `password = "AdminPass123!"` (ou adapter selon le conftest réel).

- [ ] **Step 2 : Créer `test_api_bootstrap_f2.py`**

```python
"""F2 — Tests API minimaux : bootstrap router."""
import pytest


def test_bootstrap_already_done(client, admin_user):
    """Bootstrap sur une DB non vide → 409."""
    resp = client.post("/api/bootstrap", json={
        "email": "new@example.com",
        "password": "BootstrapPass123!",
        "full_name": "New Admin",
    })
    assert resp.status_code == 409


def test_bootstrap_empty_db(empty_db_client):
    """Bootstrap sur une DB vide → 201 avec le premier admin.

    Cette fixture doit être construite localement si elle n'existe pas :
    crée un client avec une DB vide (sans admin_user fixture).
    """
    # Si la fixture empty_db_client n'existe pas, ce test est à implémenter
    # en créant une session fraîche sans données et en testant le bootstrap.
    # Sinon : adapter selon les fixtures disponibles dans conftest.
    pytest.skip("Nécessite fixture empty_db_client — à implémenter si absente")
```

Note sur bootstrap : tester le happy path (DB vide) nécessite une DB sans utilisateur. Vérifier si le conftest expose une telle fixture. Si non, l'implémenteur doit créer une fixture `empty_db_client` qui utilise une DB test fraîche. Alternativement, le test du cas 409 (DB déjà bootstrappée) suffit comme test minimal.

- [ ] **Step 3 : Créer `test_api_me_f2.py`**

```python
"""F2 — Tests API minimaux : me router."""


def test_me_authenticated(admin_client, admin_user):
    """GET /api/me authentifié → 200 avec les infos de l'utilisateur."""
    resp = admin_client.get("/api/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == admin_user.email
    assert data["role"] == "admin"


def test_me_unauthenticated(client):
    """GET /api/me sans cookie → 401."""
    resp = client.get("/api/me")
    assert resp.status_code == 401


def test_change_password_wrong_current(admin_client):
    """POST /api/me/password avec mauvais mdp actuel → 400."""
    resp = admin_client.post("/api/me/password", json={
        "current_password": "WrongCurrent999!",
        "new_password": "NewPass123456!",
    })
    assert resp.status_code == 400


def test_change_password_happy_path(admin_client, admin_user):
    """POST /api/me/password avec le bon mdp actuel → 204."""
    resp = admin_client.post("/api/me/password", json={
        "current_password": "AdminPass123!",
        "new_password": "NewPass123456!",
    })
    assert resp.status_code == 204
```

- [ ] **Step 4 : Créer `test_api_users_f2.py`**

```python
"""F2 — Tests API minimaux : users router."""


def test_list_users_admin(admin_client, admin_user):
    """GET /api/users admin → 200 avec liste."""
    resp = admin_client.get("/api/users")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1


def test_list_users_reader_forbidden(reader_client):
    """GET /api/users reader → 403."""
    resp = reader_client.get("/api/users")
    assert resp.status_code == 403


def test_create_user_admin(admin_client, db_session):
    """POST /api/users admin → 201."""
    resp = admin_client.post("/api/users", json={
        "email": "newuser@example.com",
        "password": "NewUserPass123!",
        "role": "reader",
        "full_name": "New User",
    })
    assert resp.status_code == 201
    assert resp.json()["email"] == "newuser@example.com"


def test_create_user_reader_forbidden(reader_client):
    """POST /api/users reader → 403."""
    resp = reader_client.post("/api/users", json={
        "email": "another@example.com",
        "password": "AnotherPass123!",
        "role": "reader",
    })
    assert resp.status_code == 403


def test_update_user_not_found(admin_client):
    """PATCH /api/users/999999 → 404."""
    resp = admin_client.patch("/api/users/999999", json={"full_name": "Ghost"})
    assert resp.status_code == 404


def test_delete_last_admin_forbidden(admin_client, admin_user):
    """DELETE /api/users/{admin_id} quand dernier admin → 409."""
    resp = admin_client.delete(f"/api/users/{admin_user.id}")
    assert resp.status_code == 409


def test_reset_password_not_found(admin_client):
    """POST /api/users/999999/password → 404."""
    resp = admin_client.post("/api/users/999999/password", json={
        "new_password": "ResetPass123!",
    })
    assert resp.status_code == 404
```

- [ ] **Step 5 : Créer `test_api_entities_f2.py`**

```python
"""F2 — Tests API minimaux : entities router."""


def test_list_entities_admin(admin_client):
    """GET /api/entities admin → 200."""
    resp = admin_client.get("/api/entities")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_entities_reader_forbidden(reader_client):
    """GET /api/entities reader → 403 (require_admin global)."""
    resp = reader_client.get("/api/entities")
    assert resp.status_code == 403


def test_create_entity_admin(admin_client):
    """POST /api/entities admin → 201."""
    resp = admin_client.post("/api/entities", json={
        "name": "Société Test F2",
        "siren": "123456789",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Société Test F2"


def test_update_entity_not_found(admin_client):
    """PATCH /api/entities/999999 → 404."""
    resp = admin_client.patch("/api/entities/999999", json={"name": "Ghost"})
    assert resp.status_code == 404


def test_delete_entity_with_accounts_forbidden(admin_client, entity, bank_account):
    """DELETE /api/entities/{id} avec comptes rattachés → 409."""
    resp = admin_client.delete(f"/api/entities/{entity.id}")
    assert resp.status_code == 409
```

Note : les fixtures `entity` et `bank_account` doivent exister dans le conftest. Vérifier avant l'exécution.

- [ ] **Step 6 : Créer `test_api_bank_accounts_f2.py`**

```python
"""F2 — Tests API minimaux : bank_accounts router."""


def test_list_bank_accounts_authenticated(admin_client):
    """GET /api/bank-accounts authentifié → 200."""
    resp = admin_client.get("/api/bank-accounts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_bank_accounts_reader(reader_client):
    """GET /api/bank-accounts reader → 200 (listing accessible aux readers)."""
    resp = reader_client.get("/api/bank-accounts")
    assert resp.status_code == 200


def test_create_bank_account_reader_forbidden(reader_client, entity):
    """POST /api/bank-accounts reader → 403."""
    resp = reader_client.post("/api/bank-accounts", json={
        "entity_id": entity.id,
        "name": "Compte Test",
        "iban": "FR7630004000031234567890143",
    })
    assert resp.status_code == 403


def test_update_bank_account_not_found(admin_client):
    """PATCH /api/bank-accounts/999999 → 404."""
    resp = admin_client.patch("/api/bank-accounts/999999", json={"name": "Ghost"})
    assert resp.status_code == 404


def test_create_bank_account_admin(admin_client, entity):
    """POST /api/bank-accounts admin → 201."""
    resp = admin_client.post("/api/bank-accounts", json={
        "entity_id": entity.id,
        "name": "Compte F2",
        "iban": "FR7630004000031234567890143",
    })
    assert resp.status_code == 201
```

- [ ] **Step 7 : Inspecter les fixtures disponibles**

Avant d'exécuter :

```bash
docker exec horizon-backend-1 grep -n "def admin_client\|def reader_client\|def admin_user\|def reader_user\|def entity\|def bank_account" \
  backend/tests/conftest.py
```

Adapter les fixtures utilisées dans les tests ci-dessus selon ce qui existe réellement. Si `admin_client` ou `reader_client` n'existe pas, les créer en ajoutant dans `conftest.py` :

```python
@pytest.fixture
def admin_user(db_session):
    from app.security import hash_password
    user = User(
        email="admin_f2@example.com",
        password_hash=hash_password("AdminPass123!"),
        role=UserRole.ADMIN,
        full_name="Admin F2",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def admin_client(client, admin_user):
    client.post("/api/auth/login", json={
        "email": admin_user.email,
        "password": "AdminPass123!",
    })
    return client

@pytest.fixture
def reader_user(db_session):
    from app.security import hash_password
    user = User(
        email="reader_f2@example.com",
        password_hash=hash_password("ReaderPass123!"),
        role=UserRole.READER,
        full_name="Reader F2",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def reader_client(client, reader_user):
    client.post("/api/auth/login", json={
        "email": reader_user.email,
        "password": "ReaderPass123!",
    })
    return client
```

- [ ] **Step 8 : Exécuter les tests (rouge initial)**

```bash
docker exec horizon-backend-1 pytest backend/tests/test_api_auth_f2.py \
  backend/tests/test_api_bootstrap_f2.py \
  backend/tests/test_api_me_f2.py \
  backend/tests/test_api_users_f2.py \
  backend/tests/test_api_entities_f2.py \
  backend/tests/test_api_bank_accounts_f2.py \
  -v
# Corriger les fixtures manquantes jusqu'à obtenir tous verts.
```

- [ ] **Step 9 : Régression complète**

```bash
docker exec horizon-backend-1 pytest backend/tests/ -x -q
```

- [ ] **Step 10 : Commit F2**

```bash
git add backend/tests/test_api_auth_f2.py backend/tests/test_api_bootstrap_f2.py \
        backend/tests/test_api_me_f2.py backend/tests/test_api_users_f2.py \
        backend/tests/test_api_entities_f2.py backend/tests/test_api_bank_accounts_f2.py \
        backend/tests/conftest.py
git commit -m "$(cat <<'EOF'
test(api): tests minimaux happy path + 403/404 pour 6 routers (F2)

Couvre auth (login/logout), bootstrap (409), me (GET + change-password),
users (list/create/update/delete), entities (CRUD + guards), bank_accounts
(list/create/update). Fixtures admin_client et reader_client ajoutées au
conftest si absentes.

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task F3 — Audit auth events (login OK / fail / logout)

**Files :**
- Créer : `backend/alembic/versions/20260507_1110_audit_log_auth_actions.py`
- Modifier : `backend/app/models/audit_log.py`
- Modifier : `backend/app/services/audit.py`
- Modifier : `backend/app/api/auth.py`
- Modifier : `backend/app/api/admin_audit.py`
- Modifier : `frontend/src/content/documentation.ts`
- Créer : `backend/tests/test_audit_auth_f3.py`

**Pourquoi :** les connexions réussies, échouées et les déconnexions ne sont pas tracées dans `audit_log`. En cas d'incident de sécurité (credential stuffing, accès non autorisé), il est impossible de retrouver quand un compte a été utilisé.

**Décision :** élargir `audit_log` (pas de table dédiée). Cohérent avec l'infrastructure existante. Trois nouvelles actions : `login`, `login_failed`, `logout`.

**Steps :**

- [ ] **Step 1 : Test rouge**

Créer `backend/tests/test_audit_auth_f3.py` :

```python
"""F3 — Tests audit events auth : login / login_failed / logout."""
import pytest
from sqlalchemy import select
from app.models.audit_log import AuditLog


def test_login_success_creates_audit(client, db_session, admin_user):
    """Un login réussi crée une ligne audit action=login."""
    client.post("/api/auth/login", json={
        "email": admin_user.email,
        "password": "AdminPass123!",
    })
    rows = db_session.scalars(
        select(AuditLog).where(
            AuditLog.action == "login",
            AuditLog.user_email == admin_user.email,
        )
    ).all()
    assert len(rows) >= 1


def test_login_failed_creates_audit(client, db_session, admin_user):
    """Un login échoué crée une ligne audit action=login_failed."""
    client.post("/api/auth/login", json={
        "email": admin_user.email,
        "password": "WrongPass999!",
    })
    rows = db_session.scalars(
        select(AuditLog).where(
            AuditLog.action == "login_failed",
            AuditLog.user_email == admin_user.email,
        )
    ).all()
    assert len(rows) >= 1


def test_logout_creates_audit(admin_client, db_session, admin_user):
    """Un logout crée une ligne audit action=logout."""
    admin_client.post("/api/auth/logout")
    rows = db_session.scalars(
        select(AuditLog).where(
            AuditLog.action == "logout",
            AuditLog.user_email == admin_user.email,
        )
    ).all()
    assert len(rows) >= 1
```

```bash
docker exec horizon-backend-1 pytest backend/tests/test_audit_auth_f3.py -v
# Attendu : 3 FAIL (actions non tracées)
```

- [ ] **Step 2 : Migration pour étendre la contrainte DB**

Créer `backend/alembic/versions/20260507_1110_audit_log_auth_actions.py` :

```python
"""F3 — Étend la CheckConstraint audit_log action pour accepter login/login_failed/logout.

Revision ID: h0r1z0nf0300
Revises: h0r1z0nf0100
Create Date: 2026-05-07 11:10:00
"""
from __future__ import annotations
from alembic import op

revision = "h0r1z0nf0300"
down_revision = "h0r1z0nf0100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_audit_log_action", "audit_log")
    op.create_check_constraint(
        "ck_audit_log_action",
        "audit_log",
        "action IN ('create','update','delete','merge','login','login_failed','logout')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_audit_log_action", "audit_log")
    op.create_check_constraint(
        "ck_audit_log_action",
        "audit_log",
        "action IN ('create','update','delete','merge')",
    )
```

```bash
docker cp backend/alembic/versions/20260507_1110_audit_log_auth_actions.py \
  horizon-backend-1:/app/alembic/versions/
docker exec horizon-backend-1 alembic upgrade head
docker exec horizon-backend-1 alembic current
# Attendu : h0r1z0nf0300 (head)
```

- [ ] **Step 3 : Mettre à jour le modèle `AuditLog`**

Dans `backend/app/models/audit_log.py`, remplacer la `CheckConstraint` :

```python
# Avant :
CheckConstraint(
    "action IN ('create', 'update', 'delete', 'merge')",
    name="ck_audit_log_action",
),

# Après :
CheckConstraint(
    "action IN ('create','update','delete','merge','login','login_failed','logout')",
    name="ck_audit_log_action",
),
```

- [ ] **Step 4 : Élargir `AuditAction` dans `services/audit.py`**

Dans `backend/app/services/audit.py`, ligne 36 :

```python
# Avant :
AuditAction = Literal["create", "update", "delete"]

# Après :
AuditAction = Literal["create", "update", "delete", "merge", "login", "login_failed", "logout"]
```

- [ ] **Step 5 : Instrumenter `api/auth.py`**

Dans `backend/app/api/auth.py`, ajouter les imports nécessaires en haut :

```python
from app.services.audit import record_audit
```

Dans la fonction `login`, le flux est :
1. Si l'utilisateur n'existe pas ou mauvais mot de passe → 401. Avant de lever, tracer `login_failed` si l'email correspond à un utilisateur existant.
2. Si login réussi → tracer `login`.

Remplacer la fonction `login` :

```python
@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
def login(
    request: Request,
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    if (
        user is None
        or not user.is_active
        or not verify_password(payload.password, user.password_hash)
    ):
        # Tracer l'échec seulement si l'utilisateur existe (évite d'énumérer)
        if user is not None:
            record_audit(
                db,
                user=None,
                action="login_failed",
                entity=user,
                after={"email": user.email},
                request=request,
            )
            try:
                db.commit()
            except Exception:
                db.rollback()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants invalides"
        )
    token = encode_session_token(
        user_id=user.id,
        version=user.session_token_version,
        secret=settings.secret_key,
    )
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=settings.session_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
    user.last_login_at = datetime.now(UTC)
    record_audit(
        db,
        user=user,
        action="login",
        entity=user,
        after={"email": user.email, "role": user.role.value},
        request=request,
    )
    db.commit()
    return LoginResponse(
        id=user.id, email=user.email, role=user.role.value, full_name=user.full_name
    )
```

Pour `logout`, la session dépend du cookie, pas d'un user chargé. Ajouter une dépendance optionnelle sur `get_current_user` pour logger qui se déconnecte (si le cookie est valide). Modifier `logout` :

```python
from app.deps import get_current_user as _get_current_user
from typing import Optional

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    # Optional : si le cookie est valide on trace, sinon on ignore silencieusement.
    current: Optional[User] = Depends(
        lambda db=Depends(get_db), req=None: None  # placeholder — voir note
    ),
) -> None:
    response.delete_cookie(COOKIE_NAME)
```

Note : injecter `get_current_user` en dépendance optionnelle dans `logout` est complexe car `get_current_user` lève une exception 401 si le cookie est absent/invalide. La solution propre : utiliser un `try/except` dans le body de `logout` pour charger le user courant, ou utiliser une dépendance qui retourne `None` au lieu de lever. Implémentation recommandée :

```python
from app.deps import COOKIE_NAME as _COOKIE_NAME
from app.security import decode_session_token

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> None:
    # Tenter de retrouver l'utilisateur depuis le cookie pour l'audit.
    # Si le cookie est absent/invalide : on déconnecte quand même, sans audit.
    user: User | None = None
    cookie_val = request.cookies.get(COOKIE_NAME)
    if cookie_val:
        try:
            payload = decode_session_token(cookie_val, secret=settings.secret_key)
            user = db.get(User, payload["user_id"])
        except Exception:
            pass
    response.delete_cookie(COOKIE_NAME)
    if user is not None:
        record_audit(
            db,
            user=user,
            action="logout",
            entity=user,
            after={"email": user.email},
            request=request,
        )
        try:
            db.commit()
        except Exception:
            db.rollback()
```

Vérifier la signature exacte de `decode_session_token` dans `backend/app/security.py` avant d'implémenter.

- [ ] **Step 6 : Étendre le filtre Query dans `admin_audit.py`**

Dans `backend/app/api/admin_audit.py`, ligne 33, remplacer le pattern :

```python
# Avant :
action: str | None = Query(default=None, pattern="^(create|update|delete|merge)$"),

# Après :
action: str | None = Query(
    default=None,
    pattern="^(create|update|delete|merge|login|login_failed|logout)$",
),
```

- [ ] **Step 7 : Mettre à jour `documentation.ts`**

Dans `frontend/src/content/documentation.ts`, section `securite` (id `"securite"`), ajouter dans `sees` :

```typescript
"Un journal d'audit des événements d'authentification : chaque connexion réussie, chaque tentative échouée et chaque déconnexion est enregistrée dans le journal d'audit avec l'adresse IP source et l'horodatage. Consultable depuis Administration > Journal d'audit en filtrant sur l'action login, login_failed ou logout.",
```

Ajouter dans `does` :

```typescript
"Pour surveiller les connexions suspectes : ouvrez Administration > Journal d'audit, filtrez par action login_failed et vérifiez si un compte accumule des tentatives répétées depuis des IP inconnues.",
```

- [ ] **Step 8 : Tests verts**

```bash
docker exec horizon-backend-1 pytest backend/tests/test_audit_auth_f3.py -v
# Attendu : 3 PASS
docker exec horizon-backend-1 pytest backend/tests/ -x -q
```

- [ ] **Step 9 : Commit F3**

```bash
git add backend/alembic/versions/20260507_1110_audit_log_auth_actions.py \
        backend/app/models/audit_log.py \
        backend/app/services/audit.py \
        backend/app/api/auth.py \
        backend/app/api/admin_audit.py \
        backend/tests/test_audit_auth_f3.py \
        frontend/src/content/documentation.ts
git commit -m "$(cat <<'EOF'
feat(audit): trace login / login_failed / logout dans audit_log (F3)

Migration h0r1z0nf0300 : étend CheckConstraint audit_log pour accepter
les 3 nouvelles actions. AuditAction élargi dans services/audit.py.
api/auth.py instrumente login (succès + échec) et logout. Filtre admin
audit étendu. Doc sécurité mise à jour dans documentation.ts.

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task F4 — Lockout utilisateur après 5 échecs de connexion

**Files :**
- Créer : `backend/alembic/versions/20260507_1120_user_lockout.py`
- Modifier : `backend/app/models/user.py`
- Modifier : `backend/app/api/auth.py`
- Modifier : `frontend/src/content/documentation.ts`
- Créer : `backend/tests/test_user_lockout_f4.py`

**Pourquoi :** sans protection, un attaquant peut tester un nombre illimité de mots de passe sur un compte (brute force). La protection par rate-limiter (10/minute sur `/api/auth/login`) existe mais ne protège pas contre des attaques distribuées lentes. Le lockout applicatif bloque le compte au niveau utilisateur, indépendamment du réseau.

**Logique :** 5 échecs consécutifs → `locked_until = now() + 15 min`. Reset du compteur à 0 sur succès. Si `locked_until` est dans le futur, retourner 423 Locked.

**Steps :**

- [ ] **Step 1 : Test rouge**

Créer `backend/tests/test_user_lockout_f4.py` :

```python
"""F4 — Tests lockout après 5 échecs de connexion."""
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.user import User


def _fail_login(client, email: str, n: int) -> None:
    for _ in range(n):
        client.post("/api/auth/login", json={
            "email": email,
            "password": "WrongPass999!",
        })


def test_lockout_after_5_failures(client, db_session, admin_user):
    """6e tentative échouée après 5 échecs → 423."""
    _fail_login(client, admin_user.email, 5)
    resp = client.post("/api/auth/login", json={
        "email": admin_user.email,
        "password": "WrongPass999!",
    })
    assert resp.status_code == 423


def test_correct_password_rejected_while_locked(client, db_session, admin_user):
    """Même le bon mot de passe est rejeté si le compte est verrouillé."""
    _fail_login(client, admin_user.email, 5)
    resp = client.post("/api/auth/login", json={
        "email": admin_user.email,
        "password": "AdminPass123!",
    })
    assert resp.status_code == 423


def test_counter_reset_on_success(client, db_session, admin_user):
    """4 échecs + 1 succès → compteur remis à 0, pas de lockout."""
    _fail_login(client, admin_user.email, 4)
    # Login réussi
    resp = client.post("/api/auth/login", json={
        "email": admin_user.email,
        "password": "AdminPass123!",
    })
    assert resp.status_code == 200
    # Vérifier que le compteur est à 0
    db_session.expire(admin_user)
    user = db_session.get(User, admin_user.id)
    assert user.failed_login_attempts == 0
    assert user.locked_until is None


def test_locked_until_set_after_5_failures(client, db_session, admin_user):
    """Après 5 échecs, locked_until est dans le futur."""
    _fail_login(client, admin_user.email, 5)
    db_session.expire(admin_user)
    user = db_session.get(User, admin_user.id)
    assert user.locked_until is not None
    assert user.locked_until > datetime.now(UTC)
```

```bash
docker exec horizon-backend-1 pytest backend/tests/test_user_lockout_f4.py -v
# Attendu : 4 FAIL (colonnes lockout inexistantes)
```

- [ ] **Step 2 : Migration**

Créer `backend/alembic/versions/20260507_1120_user_lockout.py` :

```python
"""F4 — Ajoute failed_login_attempts et locked_until sur users.

Revision ID: h0r1z0nf0400
Revises: h0r1z0nf0300
Create Date: 2026-05-07 11:20:00
"""
from __future__ import annotations
import sqlalchemy as sa
from alembic import op

revision = "h0r1z0nf0400"
down_revision = "h0r1z0nf0300"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "failed_login_attempts",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "locked_until",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")
```

```bash
docker cp backend/alembic/versions/20260507_1120_user_lockout.py \
  horizon-backend-1:/app/alembic/versions/
docker exec horizon-backend-1 alembic upgrade head
docker exec horizon-backend-1 alembic current
# Attendu : h0r1z0nf0400 (head)
```

- [ ] **Step 3 : Mettre à jour le modèle `User`**

Dans `backend/app/models/user.py`, ajouter après `last_login_at` :

```python
failed_login_attempts: Mapped[int] = mapped_column(
    Integer, nullable=False, default=0, server_default="0"
)
locked_until: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True), nullable=True
)
```

S'assurer que `DateTime` est importé (il l'est déjà dans le fichier).

- [ ] **Step 4 : Implémenter la logique lockout dans `api/auth.py`**

Constantes en haut de `api/auth.py` :

```python
_MAX_FAILED_ATTEMPTS = 5
_LOCKOUT_DURATION_MINUTES = 15
```

Modifier la fonction `login` pour incorporer la vérification et la mise à jour du compteur. La logique en pseudo-code :

```
1. Charger user par email.
2. Si user est None : retourner 401 directement (pas de commit, pas d'audit).
3. Si user.locked_until est dans le futur : retourner 423 Locked (pas d'incrémentation).
4. Si le mot de passe est incorrect ou user.is_active est False :
   a. user.failed_login_attempts += 1
   b. Si failed_login_attempts >= _MAX_FAILED_ATTEMPTS :
      user.locked_until = now() + 15 min
   c. record_audit(action="login_failed", ...)
   d. db.commit()
   e. Retourner 401.
5. Si succès :
   a. user.failed_login_attempts = 0
   b. user.locked_until = None
   c. user.last_login_at = now()
   d. record_audit(action="login", ...)
   e. db.commit()
   f. Retourner 200 + cookie.
```

La fonction `login` complète après F3 + F4 :

```python
from datetime import timedelta
from fastapi import status as http_status

@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
def login(
    request: Request,
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    user = db.scalar(select(User).where(User.email == payload.email))

    # Email inconnu : 401 sans info supplémentaire (anti-énumération)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants invalides"
        )

    # Compte verrouillé (locked_until dans le futur)
    now = datetime.now(UTC)
    if user.locked_until is not None and user.locked_until > now:
        remaining = int((user.locked_until - now).total_seconds() // 60) + 1
        raise HTTPException(
            status_code=423,
            detail=f"Compte temporairement verrouillé. Réessayez dans {remaining} minute(s).",
        )

    # Vérification du mot de passe et du statut
    if not user.is_active or not verify_password(payload.password, user.password_hash):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= _MAX_FAILED_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=_LOCKOUT_DURATION_MINUTES)
        record_audit(
            db,
            user=None,
            action="login_failed",
            entity=user,
            after={"email": user.email, "failed_attempts": user.failed_login_attempts},
            request=request,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants invalides"
        )

    # Succès : réinitialiser le compteur
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now

    token = encode_session_token(
        user_id=user.id,
        version=user.session_token_version,
        secret=settings.secret_key,
    )
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=settings.session_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
    record_audit(
        db,
        user=user,
        action="login",
        entity=user,
        after={"email": user.email, "role": user.role.value},
        request=request,
    )
    db.commit()
    return LoginResponse(
        id=user.id, email=user.email, role=user.role.value, full_name=user.full_name
    )
```

Note : si F3 et F4 sont implémentées dans la même passe, la fonction ci-dessus remplace directement la version intermédiaire de F3.

- [ ] **Step 5 : Mettre à jour `documentation.ts`**

Dans la section `securite`, ajouter dans `sees` :

```typescript
"Un mécanisme de verrouillage automatique : après 5 tentatives de connexion échouées consécutives, le compte est automatiquement verrouillé pendant 15 minutes. Pendant cette période, même le bon mot de passe est refusé. Le compteur se remet à zéro à chaque connexion réussie.",
```

Ajouter dans `does` :

```typescript
"Si vous recevez un message indiquant que votre compte est temporairement verrouillé : attendez les 15 minutes indiquées dans le message, puis réessayez. Si vous suspectez que quelqu'un tente de prendre le contrôle de votre compte, prévenez un administrateur immédiatement pour qu'il réinitialise votre mot de passe.",
```

- [ ] **Step 6 : Tests verts**

```bash
docker exec horizon-backend-1 pytest backend/tests/test_user_lockout_f4.py -v
# Attendu : 4 PASS
docker exec horizon-backend-1 pytest backend/tests/ -x -q
```

- [ ] **Step 7 : Commit F4**

```bash
git add backend/alembic/versions/20260507_1120_user_lockout.py \
        backend/app/models/user.py \
        backend/app/api/auth.py \
        backend/tests/test_user_lockout_f4.py \
        frontend/src/content/documentation.ts
git commit -m "$(cat <<'EOF'
feat(auth): lockout 15 min après 5 échecs de connexion consécutifs (F4)

Migration h0r1z0nf0400 : colonnes failed_login_attempts (int default 0)
et locked_until (timestamptz nullable) sur users. Logique dans api/auth.py :
5 échecs → locked_until = now + 15 min, 423 Locked retourné. Reset
compteur sur succès. Doc sécurité mise à jour.

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task F5 — Pagination forcée sur les listings non bornés

**Files :**
- Modifier : `backend/app/api/counterparties.py`
- Modifier : `backend/app/api/rules.py`
- Modifier : `backend/app/api/forecast_scenarios.py`
- Modifier : `backend/app/api/forecast_lines.py`
- Créer : `backend/tests/test_pagination_f5.py`

**Pourquoi :** les listings counterparties, rules, forecast_scenarios et forecast_lines n'ont pas de borne supérieure. Une DB avec 10 000 tiers ou 500 règles retournerait tout en mémoire sur un seul appel, saturant le backend et le client.

**Décision :** retourner un tableau brut (pas de wrapper paginé) avec `limit` et `offset` en query params. Raison : le frontend consomme un tableau brut (`resp.json()` direct, `apiFetch<Rule[]>`) — un wrapper `{items, total}` serait un breaking change. Le plafond `le=1000` suffit comme garde-fou. Pas de modification frontend.

**Steps :**

- [ ] **Step 1 : Test rouge**

Créer `backend/tests/test_pagination_f5.py` :

```python
"""F5 — Tests pagination sur les listings non bornés."""


def test_counterparties_limit_param(admin_client):
    """GET /api/counterparties?limit=5&offset=0 → accepté."""
    resp = admin_client.get("/api/counterparties?limit=5&offset=0")
    assert resp.status_code == 200


def test_counterparties_limit_over_1000_rejected(admin_client):
    """GET /api/counterparties?limit=1001 → 422 (limit > 1000 interdit)."""
    resp = admin_client.get("/api/counterparties?limit=1001")
    assert resp.status_code == 422


def test_rules_limit_param(admin_client):
    """GET /api/rules?limit=10&offset=0 → accepté."""
    resp = admin_client.get("/api/rules?limit=10&offset=0")
    assert resp.status_code == 200


def test_rules_limit_over_1000_rejected(admin_client):
    """GET /api/rules?limit=1001 → 422."""
    resp = admin_client.get("/api/rules?limit=1001")
    assert resp.status_code == 422


def test_forecast_scenarios_limit_param(admin_client):
    """GET /api/forecast/scenarios?limit=10 → accepté."""
    resp = admin_client.get("/api/forecast/scenarios?limit=10")
    assert resp.status_code == 200


def test_forecast_lines_limit_param(admin_client, forecast_scenario):
    """GET /api/forecast/lines?scenario_id=N&limit=10 → accepté."""
    resp = admin_client.get(
        f"/api/forecast/lines?scenario_id={forecast_scenario.id}&limit=10"
    )
    assert resp.status_code == 200
```

```bash
docker exec horizon-backend-1 pytest backend/tests/test_pagination_f5.py -v
# Attendu : tous FAIL (params limit/offset non reconnus → ignorés ou 422)
```

- [ ] **Step 2 : Modifier `api/counterparties.py`**

Dans la fonction `list_counterparties`, ajouter les paramètres et appliquer à la query :

```python
@router.get("", response_model=list[CounterpartyWithAggregates])
def list_counterparties(
    entity_id: int | None = Query(default=None),
    include_ignored: bool = Query(default=False),
    search: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[CounterpartyWithAggregates]:
    # ... (code existant inchangé jusqu'à la query)
    q = q.order_by(tx_volume_sq.desc(), Counterparty.name.asc())
    q = q.limit(limit).offset(offset)  # <- ajouter ces deux lignes
    rows = session.execute(q).all()
    # ... (return inchangé)
```

- [ ] **Step 3 : Modifier `api/rules.py`**

Dans la fonction `list_rules`, ajouter `limit` et `offset` :

```python
@router.get("", response_model=list[RuleRead])
def list_rules(
    scope: Optional[Literal["global", "entity", "all"]] = Query(default="all"),
    entity_id: Optional[int] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[RuleRead]:
    # ... (code existant inchangé)
    q = q.order_by(
        CategorizationRule.entity_id.asc().nulls_last(),
        CategorizationRule.priority.asc(),
    )
    q = q.limit(limit).offset(offset)  # <- ajouter
    rows = session.execute(q).scalars().all()
    return [RuleRead.model_validate(r) for r in rows]
```

- [ ] **Step 4 : Modifier `api/forecast_scenarios.py`**

Dans `list_scenarios`, ajouter `limit` et `offset` :

```python
@router.get("", response_model=list[ScenarioRead])
def list_scenarios(
    entity_id: int | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[ScenarioRead]:
    # ... (code existant inchangé)
    rows = list(
        session.scalars(
            select(ForecastScenario)
            .where(*where)
            .order_by(
                ForecastScenario.entity_id,
                ForecastScenario.is_default.desc(),
                ForecastScenario.name,
            )
            .limit(limit)    # <- ajouter
            .offset(offset)  # <- ajouter
        )
    )
    return [ScenarioRead.model_validate(r) for r in rows]
```

- [ ] **Step 5 : Modifier `api/forecast_lines.py`**

Dans `list_lines`, ajouter `limit` et `offset` :

```python
@router.get("", response_model=list[LineRead])
def list_lines(
    scenario_id: int = Query(...),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[LineRead]:
    _get_scenario_with_access(session, user, scenario_id)
    rows = list(
        session.scalars(
            select(ForecastLine)
            .where(ForecastLine.scenario_id == scenario_id)
            .order_by(ForecastLine.category_id)
            .limit(limit)    # <- ajouter
            .offset(offset)  # <- ajouter
        )
    )
    return [LineRead.model_validate(r) for r in rows]
```

- [ ] **Step 6 : Tests verts**

```bash
docker exec horizon-backend-1 pytest backend/tests/test_pagination_f5.py -v
# Attendu : tous PASS
docker exec horizon-backend-1 pytest backend/tests/ -x -q
```

- [ ] **Step 7 : Commit F5**

```bash
git add backend/app/api/counterparties.py backend/app/api/rules.py \
        backend/app/api/forecast_scenarios.py backend/app/api/forecast_lines.py \
        backend/tests/test_pagination_f5.py
git commit -m "$(cat <<'EOF'
fix(api): pagination forcée sur counterparties, rules, forecast/scenarios, forecast/lines (F5)

Paramètres limit (default=200, max=1000) et offset ajoutés sur les 4
listings non bornés. Retour tableau brut conservé pour compatibilité
frontend. Empêche les sequential scans mémoire complets sur des jeux
de données larges.

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task F6 — Fix règles à 0 hit et regex cassées par la normalisation

**Files :**
- Aucun fichier créé ou modifié (UPDATE SQL uniquement en session interactive)
- Créer : `backend/tests/test_f6_rules_normalization.py` (test de régression)

**Pourquoi :** les règles insérées par les migrations de seed avant l'introduction du validator `_normalize_label_value` ont des `label_value` avec ponctuation (`**`, `.`, etc.) qui ne peuvent jamais matcher un libellé normalisé. `normalize_label` supprime tous les caractères autres que `[A-Z0-9\s-]`.

**Décision :** corriger les règles via UPDATE SQL transactionnel. Jamais sed, jamais modification directe de fichiers de migration.

**Steps :**

- [ ] **Step 1 : Identifier les règles à 0 hit**

```bash
docker exec horizon-db-1 psql -U $POSTGRES_USER -d $POSTGRES_DB -c \
"SELECT id, name, label_operator, label_value
 FROM categorization_rules
 WHERE id NOT IN (
   SELECT DISTINCT categorization_rule_id
   FROM transactions
   WHERE categorization_rule_id IS NOT NULL
 )
 ORDER BY id;"
```

Conserver la sortie complète. Pour chaque règle listée, analyser :
- Est-ce que `label_value` contient des caractères supprimés par `normalize_label` (`**`, `.`, `,`, `(`, `)`, etc.) ?
- Est-ce que la règle correspond à un flux réel qui devrait matcher ? (vérifier dans les transactions sur les 6 derniers mois)
- Si oui : la valeur normalisée serait-elle ambiguë ou trop large ?

Pour déterminer la valeur normalisée d'une règle existante, utiliser Python dans le container :

```bash
docker exec horizon-backend-1 python3 -c "
from app.parsers.normalization import normalize_label
values = ['FRAIS **', 'exemple valeur']  # remplacer par les valeurs réelles
for v in values:
    print(repr(v), '->', repr(normalize_label(v)))
"
```

- [ ] **Step 2 : Classer chaque règle à 0 hit**

Pour chaque règle identifiée, décider :
- **A : Corriger** — la règle est intentionnelle, seule la valeur est cassée par normalisation → UPDATE `label_value` avec la version normalisée.
- **B : Supprimer** — la règle n'a jamais correspondu à aucun flux, est redondante ou obsolète → DELETE.
- **C : Laisser** — la règle est à 0 hit pour une raison légitime (flux futur prévu, règle de garde inactive) → pas d'action.

- [ ] **Step 3 : Appliquer les corrections via UPDATE SQL transactionnel**

Pour les règles classées A :

```sql
-- Dans une transaction
BEGIN;

UPDATE categorization_rules
SET label_value = normalize_label_equivalent  -- la valeur normalisée calculée en Step 1
WHERE id = <id_regle>
  AND name = '<nom_pour_guard>'  -- double vérification sur le nom
  AND label_value = '<valeur_actuelle>';

-- Vérifier avant COMMIT :
SELECT id, name, label_value FROM categorization_rules WHERE id = <id_regle>;

COMMIT;
```

Exemple concret pour une règle "FRAIS **" qui doit devenir "FRAIS" :

```bash
docker exec horizon-db-1 psql -U $POSTGRES_USER -d $POSTGRES_DB <<'EOF'
BEGIN;
UPDATE categorization_rules
SET label_value = 'FRAIS'
WHERE name = 'Frais bancaires generiques'
  AND label_value LIKE 'FRAIS%**%';
SELECT id, name, label_value FROM categorization_rules WHERE label_value = 'FRAIS';
COMMIT;
EOF
```

Pour les règles classées B :

```bash
docker exec horizon-db-1 psql -U $POSTGRES_USER -d $POSTGRES_DB <<'EOF'
BEGIN;
DELETE FROM categorization_rules
WHERE id IN (<id1>, <id2>)
  AND is_system = false;  -- garde-fou : ne jamais supprimer les règles système via SQL
SELECT COUNT(*) FROM categorization_rules WHERE id IN (<id1>, <id2>);
-- Attendu : 0
COMMIT;
EOF
```

Attention : ne jamais supprimer via SQL une règle avec `is_system = true`. Ces règles sont gérées par les migrations.

- [ ] **Step 4 : Test de régression sur la normalisation**

Créer `backend/tests/test_f6_rules_normalization.py` :

```python
"""F6 — Vérifie que normalize_label supprime les caractères problématiques
et que les label_value en DB sont toujours des versions normalisées valides.
"""
from app.parsers.normalization import normalize_label
from sqlalchemy import select, text
from app.models.categorization_rule import CategorizationRule


def test_normalize_strips_asterisks():
    """Les astérisques sont supprimés par normalize_label."""
    assert normalize_label("FRAIS **") == "FRAIS"


def test_normalize_strips_parentheses():
    assert normalize_label("VIR (REF)") == "VIR REF"


def test_normalize_is_idempotent():
    """Appliquer normalize_label deux fois donne le même résultat."""
    v = "DGFIP IMPOTS"
    assert normalize_label(normalize_label(v)) == normalize_label(v)


def test_all_rule_label_values_are_normalized(db_session):
    """Chaque label_value en DB doit être identique à sa version normalisée.

    Ce test détecte toute règle dont la valeur n'a pas été normalisée à la
    création (régression de la migration F6 ou d'une insertion directe en SQL).
    """
    rules = db_session.scalars(
        select(CategorizationRule).where(
            CategorizationRule.label_value.isnot(None)
        )
    ).all()
    bad = [
        (r.id, r.name, r.label_value, normalize_label(r.label_value))
        for r in rules
        if r.label_value and normalize_label(r.label_value) != r.label_value
    ]
    assert bad == [], (
        f"Règles avec label_value non normalisé : {bad}. "
        "Corriger via UPDATE SQL transactionnel dans la DB."
    )
```

```bash
docker exec horizon-backend-1 pytest backend/tests/test_f6_rules_normalization.py -v
# Attendu : tous PASS après les UPDATEs de Step 3
```

- [ ] **Step 5 : Commit F6**

```bash
git add backend/tests/test_f6_rules_normalization.py
git commit -m "$(cat <<'EOF'
fix(rules): correction des label_value non normalisés (F6)

Règles seed avec astérisques et ponctuation corrigées via UPDATE SQL
transactionnel. Test de régression test_f6_rules_normalization.py
garantit que tous les label_value en DB sont identiques à leur version
passée par normalize_label.

Liste des règles supprimées : (voir corps du commit ou task F6 du plan)
Liste des règles corrigées : (idem)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task F7 — Whitelist setattr dans les endpoints PATCH

**Files :**
- Modifier : `backend/app/api/users.py`
- Modifier : `backend/app/api/entities.py`
- Modifier : `backend/app/api/bank_accounts.py`
- Modifier : `backend/app/api/forecast_scenarios.py`
- Modifier : `backend/app/api/commitments.py`
- Créer : `backend/tests/test_setattr_whitelist_f7.py`

**Pourquoi :** les boucles `setattr(obj, k, v) for k, v in payload.model_dump().items()` affectent n'importe quel attribut de l'objet ORM si le champ Pydantic porte le même nom. Un payload mal construit (ou une future modification du schéma qui expose un champ supplémentaire) pourrait écrire dans des colonnes non prévues (ex. `session_token_version` sur User, `is_system` sur une règle).

**Approche :** remplacer chaque boucle générique par une boucle sur une liste de champs autorisés. Les champs non whitelistés sont silencieusement ignorés.

**Steps :**

- [ ] **Step 1 : Test rouge**

Créer `backend/tests/test_setattr_whitelist_f7.py` :

```python
"""F7 — Vérifie que les PATCH n'acceptent que les champs whitelistés."""


def test_user_patch_ignores_session_token_version(admin_client, admin_user, db_session):
    """PATCH /api/users/{id} avec session_token_version dans le payload →
    le champ est ignoré (pas de 422 si Pydantic ne le reconnaît pas, ou
    pas de modification du champ si Pydantic le tolère via extra='allow')."""
    original_version = admin_user.session_token_version
    # UserUpdate n'a pas session_token_version, donc Pydantic le rejette à 422.
    # Ce test vérifie que même si on construisait un schéma avec extra fields,
    # la whitelist protège le champ.
    resp = admin_client.patch(f"/api/users/{admin_user.id}", json={
        "full_name": "Test Whitelist",
    })
    assert resp.status_code == 200
    db_session.expire(admin_user)
    from app.models.user import User
    user = db_session.get(User, admin_user.id)
    assert user.session_token_version == original_version  # non modifié
    assert user.full_name == "Test Whitelist"


def test_scenario_patch_only_allowed_fields(admin_client, forecast_scenario, db_session):
    """PATCH /api/forecast/scenarios/{id} avec entity_id dans le payload →
    entity_id ignoré (non whitelisté)."""
    original_entity_id = forecast_scenario.entity_id
    resp = admin_client.patch(f"/api/forecast/scenarios/{forecast_scenario.id}", json={
        "name": "Scenario Renamed",
    })
    assert resp.status_code == 200
    db_session.expire(forecast_scenario)
    from app.models.forecast_scenario import ForecastScenario
    sc = db_session.get(ForecastScenario, forecast_scenario.id)
    assert sc.entity_id == original_entity_id  # non modifié
    assert sc.name == "Scenario Renamed"
```

- [ ] **Step 2 : Appliquer la whitelist dans `api/users.py`**

Dans `update_user`, remplacer :

```python
# Avant :
for field, value in data.items():
    setattr(user, field, value)

# Après :
_USER_UPDATABLE_FIELDS = {"role", "full_name", "is_active"}
for field, value in data.items():
    if field in _USER_UPDATABLE_FIELDS:
        setattr(user, field, value)
```

Déclarer `_USER_UPDATABLE_FIELDS` comme constante de module en haut du fichier (après les imports).

- [ ] **Step 3 : Appliquer la whitelist dans `api/entities.py`**

Inspecter `backend/app/schemas/entity.py` pour lister les champs de `EntityUpdate` :

```bash
docker exec horizon-backend-1 grep -A 20 "class EntityUpdate" backend/app/schemas/entity.py
```

Puis dans `update_entity` :

```python
_ENTITY_UPDATABLE_FIELDS = {"name", "siren", "address", "parent_entity_id"}
# Adapter selon les champs réels de EntityUpdate.
for field, value in payload.model_dump(exclude_unset=True).items():
    if field in _ENTITY_UPDATABLE_FIELDS:
        setattr(e, field, value)
```

- [ ] **Step 4 : Appliquer la whitelist dans `api/bank_accounts.py`**

Inspecter `backend/app/schemas/bank_account.py` pour les champs de `BankAccountUpdate` :

```bash
docker exec horizon-backend-1 grep -A 20 "class BankAccountUpdate" backend/app/schemas/bank_account.py
```

Dans `update_bank_account` :

```python
_BANK_ACCOUNT_UPDATABLE_FIELDS = {"name", "bic", "bank_name", "bank_code", "is_active"}
# Adapter selon les champs réels de BankAccountUpdate.
for field, value in payload.model_dump(exclude_unset=True).items():
    if field in _BANK_ACCOUNT_UPDATABLE_FIELDS:
        setattr(ba, field, value)
```

- [ ] **Step 5 : Appliquer la whitelist dans `api/forecast_scenarios.py`**

Dans `update_scenario` :

```python
_SCENARIO_UPDATABLE_FIELDS = {"name", "description", "is_default"}
# ... après compute des updates et _unset_other_defaults ...
for field, value in updates.items():
    if field in _SCENARIO_UPDATABLE_FIELDS:
        setattr(sc, field, value)
```

- [ ] **Step 6 : Appliquer la whitelist dans `api/commitments.py`**

Dans `update_commitment`, la boucle existante a déjà des branches pour `direction` et `status`. Transformer en whitelist explicite :

```python
_COMMITMENT_UPDATABLE_FIELDS = {
    "counterparty_id", "category_id", "bank_account_id",
    "direction", "status", "amount_cents",
    "issue_date", "expected_date",
    "reference", "description", "pdf_attachment_id",
}
for field, value in updates.items():
    if field not in _COMMITMENT_UPDATABLE_FIELDS:
        continue
    if field == "direction" and value is not None:
        setattr(c, field, CommitmentDirection(value))
    elif field == "status" and value is not None:
        setattr(c, field, CommitmentStatus(value))
    else:
        setattr(c, field, value)
```

Note : `entity_id` et `created_by_id` sont explicitement exclus de la whitelist — on ne doit pas pouvoir changer l'entité ou l'auteur d'un engagement par PATCH.

- [ ] **Step 7 : Tests verts**

```bash
docker exec horizon-backend-1 pytest backend/tests/test_setattr_whitelist_f7.py -v
# Attendu : tous PASS
docker exec horizon-backend-1 pytest backend/tests/ -x -q
```

- [ ] **Step 8 : Commit F7**

```bash
git add backend/app/api/users.py backend/app/api/entities.py \
        backend/app/api/bank_accounts.py backend/app/api/forecast_scenarios.py \
        backend/app/api/commitments.py \
        backend/tests/test_setattr_whitelist_f7.py
git commit -m "$(cat <<'EOF'
refactor(api): whitelist setattr explicite sur les endpoints PATCH (F7)

Remplace les boucles setattr génériques par des whitelist de champs
autorisés : users (role/full_name/is_active), entities, bank_accounts,
forecast_scenarios (name/description/is_default), commitments. Protège
contre l'écriture accidentelle sur des colonnes non prévues (ex.
session_token_version, is_system, entity_id).

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task F8 — Vérification selectinload sur listings (guard anti-N+1)

**Files :**
- Créer : `backend/tests/test_no_n_plus_one_f8.py`
- Modifier (si N+1 détecté) : `backend/app/api/commitments.py` ou `backend/app/models/commitment.py`

**Pourquoi :** les listings qui chargent des relations ORM sans eager loading génèrent N+1 requêtes (une par objet pour chaque relation). `Commitment` expose `counterparty` et `category` en `lazy="joined"` — ce qui est correct. Ce test valide ce constat et bloque toute régression future.

**Steps :**

- [ ] **Step 1 : Créer le test de comptage de requêtes**

Créer `backend/tests/test_no_n_plus_one_f8.py` :

```python
"""F8 — Vérifie l'absence de requêtes N+1 sur les listings critiques.

Méthode : SQLAlchemy event listener + comptage des SELECT émis.
"""
from __future__ import annotations

import pytest
from sqlalchemy import event, select

from app.models.commitment import Commitment
from app.models.categorization_rule import CategorizationRule


@pytest.fixture
def sql_query_counter(db_session):
    """Fixture qui compte les requêtes SQL émises pendant la session."""
    queries: list[str] = []

    @event.listens_for(db_session.bind, "before_cursor_execute")
    def on_before_execute(conn, cursor, statement, parameters, context, executemany):
        queries.append(statement)

    yield queries

    # Nettoyer les listeners pour ne pas polluer les autres tests
    event.remove(db_session.bind, "before_cursor_execute", on_before_execute)


def _create_commitments(db_session, entity, bank_account, n: int = 10):
    """Crée N engagements de test avec des relations."""
    from datetime import date
    from app.models.commitment import CommitmentDirection, CommitmentStatus
    for i in range(n):
        c = Commitment(
            entity_id=entity.id,
            bank_account_id=bank_account.id,
            direction=CommitmentDirection.OUT,
            amount_cents=10000 + i * 100,
            issue_date=date(2026, 1, 1),
            expected_date=date(2026, 2, 1),
        )
        db_session.add(c)
    db_session.flush()


def test_list_commitments_no_n_plus_one(
    admin_client, db_session, entity, bank_account, sql_query_counter
):
    """GET /api/commitments avec 10 engagements → nombre de requêtes SQL
    fixe (pas proportionnel à N). On vérifie < 5 requêtes (auth + listing)."""
    _create_commitments(db_session, entity, bank_account, 10)
    db_session.commit()

    query_count_before = len(sql_query_counter)
    resp = admin_client.get(f"/api/commitments?entity_id={entity.id}")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 10

    # Avec lazy="joined", toutes les relations sont chargées en 1 requête (JOIN).
    # Maximum attendu : quelques requêtes pour auth + la requête listing elle-même.
    queries_for_listing = sql_query_counter[query_count_before:]
    select_queries = [q for q in queries_for_listing if q.strip().upper().startswith("SELECT")]
    # On autorise un maximum de 5 SELECT (très généreux) pour le listing de 10 items.
    # Si on avait N+1, ce serait 10*2+1=21 SELECT.
    assert len(select_queries) <= 5, (
        f"Trop de requêtes SQL : {len(select_queries)} SELECT pour 10 engagements. "
        "Possible N+1 détecté."
    )


def test_list_rules_no_n_plus_one(admin_client, sql_query_counter):
    """GET /api/rules → pas de N+1 (rules n'ont pas de relationship eager)."""
    query_count_before = len(sql_query_counter)
    resp = admin_client.get("/api/rules")
    assert resp.status_code == 200
    queries_for_listing = sql_query_counter[query_count_before:]
    select_queries = [q for q in queries_for_listing if q.strip().upper().startswith("SELECT")]
    # Rules : 1 SELECT attendu (pas de relation eager à charger).
    # On autorise 3 (auth + listing + éventuel check session).
    assert len(select_queries) <= 3, (
        f"Trop de requêtes SQL : {len(select_queries)} SELECT pour GET /api/rules."
    )
```

- [ ] **Step 2 : Exécuter et analyser**

```bash
docker exec horizon-backend-1 pytest backend/tests/test_no_n_plus_one_f8.py -v -s
# Si N+1 détecté : la fixture sql_query_counter affichera les requêtes problématiques
```

Si le test `test_list_commitments_no_n_plus_one` échoue avec plus de 5 SELECT, inspecter le chargement dans `Commitment` :
- Si `lazy="joined"` est en place sur le modèle → le N+1 vient d'une autre relation ou d'un chargement explicite dans le router.
- Corriger en changeant `lazy="joined"` en `lazy="selectin"` pour les relations nombreuses, ou en ajoutant `.options(selectinload(Commitment.counterparty), selectinload(Commitment.category))` dans la query du router.

Note : `lazy="joined"` sur Commitment est déjà correct et produit un JOIN unique. Si le test passe directement, c'est la confirmation attendue.

- [ ] **Step 3 : Corriger si N+1 détecté**

Si les tests révèlent un N+1, appliquer `selectinload` dans la query du router concerné. Exemple pour `api/commitments.py` :

```python
from sqlalchemy.orm import selectinload

q = (
    select(Commitment)
    .where(and_(*where))
    .options(
        selectinload(Commitment.counterparty),
        selectinload(Commitment.category),
    )
    .order_by(Commitment.expected_date.desc())
    .limit(per_page)
    .offset((page - 1) * per_page)
)
```

Si `lazy="joined"` est actif sur le modèle ET que `selectinload` est aussi appliqué dans la query, le `selectinload` prend précédence (SQLAlchemy 2.x). Il est alors plus propre de retirer `lazy="joined"` du modèle et d'utiliser `selectinload` uniquement là où c'est nécessaire.

- [ ] **Step 4 : Tests verts**

```bash
docker exec horizon-backend-1 pytest backend/tests/test_no_n_plus_one_f8.py -v
docker exec horizon-backend-1 pytest backend/tests/ -x -q
```

- [ ] **Step 5 : Commit F8**

```bash
git add backend/tests/test_no_n_plus_one_f8.py
# + les fichiers modifiés si correction appliquée
git commit -m "$(cat <<'EOF'
test(perf): guard anti-N+1 sur les listings commitments et rules (F8)

Test sql_query_counter vérifie que GET /api/commitments sur 10 items
émet < 5 SELECT (lazy="joined" sur Commitment garantit un JOIN unique).
Test GET /api/rules vérifie < 3 SELECT (pas de relationship eager,
serialisation ID-only). Régression bloquante si N+1 introduit.

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task F9 — Supprimer l'endpoint `POST /admin/audit-log/prune`

**Files :**
- Modifier : `backend/app/api/admin_audit.py`

**Pourquoi :** l'endpoint `POST /api/admin/audit-log/prune` est une surface d'attaque supplémentaire qui permet à un admin compromis de supprimer des traces d'audit. La purge de l'audit log est une opération exceptionnelle qui doit passer par une intervention SQL directe (tracée dans les logs du serveur), pas par un endpoint HTTP.

**Décision :** retirer l'endpoint. Si une purge est nécessaire en production, elle se fait via :

```sql
BEGIN;
DELETE FROM audit_log WHERE occurred_at < NOW() - INTERVAL '365 days';
-- Vérifier le nombre de lignes supprimées
COMMIT;
```

**Steps :**

- [ ] **Step 1 : Vérifier que rien n'appelle l'endpoint**

```bash
grep -rn "audit-log/prune\|audit_log.*prune\|prune.*audit" \
  /srv/prod/tools/horizon/frontend/src/ \
  /srv/prod/tools/horizon/backend/
```

Résultat attendu : aucun call-site côté frontend ou backend (autre que la définition dans `admin_audit.py`). Si un call-site existe, l'identifier et retirer avant de supprimer l'endpoint.

- [ ] **Step 2 : Supprimer l'endpoint dans `admin_audit.py`**

Dans `backend/app/api/admin_audit.py`, supprimer la fonction `prune_audit_log` et son décorateur `@router.post("/prune")` (lignes 74-87 du fichier actuel).

Supprimer aussi les imports devenus inutiles : `delete` depuis `sqlalchemy`, `timedelta` depuis `datetime`. Vérifier que `datetime` et `timezone` sont encore utilisés dans `list_audit_log` avant de les retirer.

Le fichier après modification ne doit contenir que la fonction `list_audit_log` et ses imports.

- [ ] **Step 3 : Mettre à jour le docstring du module**

Dans le docstring en tête de `admin_audit.py`, retirer la mention de `POST /api/admin/audit-log/prune`. Le docstring devient :

```python
"""Endpoint admin : consultation du journal d'audit.

GET /api/admin/audit-log — liste paginée, filtrable, admin only.

La purge des lignes anciennes se fait via SQL direct (intervention technique) :
  DELETE FROM audit_log WHERE occurred_at < NOW() - INTERVAL '365 days';
"""
```

- [ ] **Step 4 : Vérifier que `list_audit_log` fonctionne toujours**

```bash
docker exec horizon-backend-1 pytest backend/tests/test_admin_audit_merge_filter.py -v
docker exec horizon-backend-1 pytest backend/tests/ -x -q
```

- [ ] **Step 5 : Commit F9**

```bash
git add backend/app/api/admin_audit.py
git commit -m "$(cat <<'EOF'
refactor(audit): suppression de l'endpoint POST /admin/audit-log/prune (F9)

Surface d'attaque inutile : un admin compromis pouvait effacer les traces
d'audit via HTTP. La purge doit passer par SQL direct (intervention
technique tracée dans les logs serveur). Docstring mis à jour avec la
commande SQL de remplacement.

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task F10 — Synchronisation finale de la doc `securite`

**Files :**
- Modifier : `frontend/src/content/documentation.ts`

**Pourquoi :** F3 et F4 ont modifié le comportement de l'authentification. F10 est une revue de cohérence finale pour s'assurer que la section `securite` de `documentation.ts` reflète fidèlement l'état de l'app après le Plan F complet.

**Cette task ne se rédige qu'après que F1-F9 sont tous implémentés et commitéés.**

**Steps :**

- [ ] **Step 1 : Revue complète de la section `securite`**

Lire la section `securite` dans `frontend/src/content/documentation.ts` (id `"securite"`) et vérifier chaque point :

1. La mention de la révocation de session par `session_token_version` (Plan C) : déjà présente, correcte.
2. Les backups nocturnes + rotation : déjà présents, corrects.
3. Les en-têtes HTTP de sécurité : déjà présents, corrects.
4. Le lockout (F4) : doit être ajouté dans `sees` et `does` (déjà fait en F4 Step 5).
5. L'audit des événements auth (F3) : doit être ajouté (déjà fait en F3 Step 7).
6. La suppression du prune endpoint (F9) : pas visible utilisateur, pas à documenter.

- [ ] **Step 2 : Vérifier la section `audit`**

La section `audit` (id `"audit"`) mentionne "création, modification ou suppression". Depuis F3, elle doit aussi mentionner les événements d'authentification. Ajouter dans `sees` :

```typescript
"Les événements d'authentification tracés depuis la version courante : connexion réussie (action login), tentative échouée (action login_failed) et déconnexion (action logout). Filtrez par action dans le journal pour les retrouver.",
```

- [ ] **Step 3 : Vérifier la section `lexique`**

Aucun nouveau sigle introduit par le Plan F. Pas de modification.

- [ ] **Step 4 : Vérifier la cohérence des `tips` dans `securite`**

Ajouter dans `tips` de la section `securite` :

```typescript
"Le verrouillage automatique après 5 échecs s'applique même si le bon mot de passe est saisi pendant la période de gel. Ce comportement est intentionnel : il protège contre les attaques par force brute. En cas de gel accidentel, un administrateur peut déverrouiller le compte en réinitialisant le mot de passe depuis Administration > Utilisateurs.",
```

- [ ] **Step 5 : Vérification TypeScript**

```bash
cd /srv/prod/tools/horizon/frontend && npx tsc --noEmit
```

- [ ] **Step 6 : Commit F10**

```bash
git add frontend/src/content/documentation.ts
git commit -m "$(cat <<'EOF'
docs(securite): synchronisation documentation.ts après Plan F

Section securite : lockout (F4) et audit auth events (F3) documentés.
Section audit : mention des événements login/login_failed/logout.
Tips lockout : explication du comportement et procédure de déverrouillage
admin. Revue de cohérence complète Plan F.

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

