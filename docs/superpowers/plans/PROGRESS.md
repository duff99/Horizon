# Suivi d'avancement — Plan 0 Fondation

**Dernière mise à jour** : 2026-04-16 — fin Section D

## État global

- **Plan en cours** : Plan 0 — Fondation
- **Mode d'exécution** : exécution directe par l'agent (les fichiers sont entièrement spec'd dans Plan 0). Pragmatique et plus économe en tokens que le subagent-driven strict.
- **Branche Git** : `main`
- **Dernière tâche terminée** : **D4** — modèle BankAccount + tests
- **Prochaine tâche à faire** : **E1** — Hashage Argon2 (`backend/app/security.py`)
- **Avancement** : **~40 %** (4 sections sur 10, 18 tâches sur 46)

## Comment reprendre à la prochaine session

Dis simplement : *"Reprends Plan 0 là où on en est, regarde docs/superpowers/plans/PROGRESS.md"*.
Je lirai ce fichier + le `git log` pour comprendre l'état et reprendre la tâche suivante.

## Sections

| Section | Tâches | Statut |
|---|---|---|
| A — Initialisation du dépôt | A1-A5 | ✅ Terminée |
| B — Environnement Python | B1-B4 | ✅ Terminée (pytest + ruff validés) |
| C — Base de données | C1-C5 | ✅ Terminée (à valider avec Docker démarré) |
| D — Modèles ORM | D1-D4 | ✅ Terminée (migration consolidée) |
| E — Sécurité | E1-E5 | ⏳ À faire |
| F — API REST | F1-F6 | ⏳ À faire |
| G — Santé / observabilité | G1-G2 | ⏳ À faire |
| H — Frontend scaffold | H1-H5 | ⏳ À faire |
| I — Frontend admin pages | I1-I6 | ⏳ À faire |
| J — Docker orchestration | J1-J4 | ⏳ À faire |

**Total : 46 tâches**

## Notes d'exécution

- **Section A** : tâches purement de scaffolding (gitignore, README, .env.example, doc dev). Exécution directe par l'agent principal (pas de dispatch de sous-agents pour gagner du temps/token : pas de code à tester).
- **Sections B → J** : subagent-driven strict (implementer + spec reviewer + code quality reviewer pour chaque tâche avec du code).

## Journal des sections

### Section A — Initialisation du dépôt ✅

**Durée** : ~5 minutes | **Commits** : 4

- A1 ✅ `.gitignore` + `README.md` créés
- A2 ✅ Dossiers `backend/`, `frontend/`, `docs/operations/` créés (avec `.gitkeep`)
- A3 ✅ `.env.example` racine créé
- A4 ✅ `docs/operations/local-dev.md` créé
- A5 ⏭️ (rappel nettoyage `.gitkeep` à la tâche J4, pas d'action ici)

**Note** : exécution directe par l'agent principal (pas de dispatch de sous-agents) car ces tâches sont purement du scaffolding/documentation sans code à tester.

### Section B — Environnement Python ✅

**Durée** : ~10 minutes | **Commits** : 4

- B1 ✅ `backend/pyproject.toml` créé (FastAPI + SQLAlchemy + Alembic + tests)
- B2 ✅ `backend/app/main.py` (FastAPI minimal avec endpoint `/`), `backend/tests/test_health_basic.py`, `backend/tests/conftest.py` (vide pour l'instant), `backend/app/__init__.py`, `backend/tests/__init__.py`
- B3 ✅ `backend/scripts/check.sh` + `backend/scripts/check.ps1` (lance ruff/mypy/pytest)
- B4 ✅ `backend/app/config.py` (pydantic-settings avec validation), `backend/tests/test_config.py`, `backend/.env.example`

**✅ Validations exécutées avec succès** :

```
venv créé dans backend/.venv
pip install -e ".[dev]"  → OK (FastAPI, SQLAlchemy, pydantic, pytest, ruff, mypy, etc.)
pytest tests/ -v         → 3/3 PASSED, couverture 96 %
ruff check + format      → All checks passed (après auto-fix d'un ordering d'imports)
```

**⚠️ mypy** : le binaire mypy ne charge pas dans l'environnement actuel (DLL `base64` bloquée par "Application Control Policy" Windows — problème local, pas un bug du code). **À valider côté dev par l'utilisateur** dans son environnement de travail normal :

```bash
cd backend
.venv\Scripts\activate
mypy app tests
```

Si ça plante aussi côté utilisateur : vérifier Windows Defender / AppLocker / Smart App Control. Sinon, la validation mypy pourra se faire plus tard (la section C1 n'en dépend pas).

### Section C — Base de données ✅

**Commits** : 4

- C1 ✅ `docker-compose.dev.yml` avec service Postgres 16 + healthcheck + volume persistant
- C2 ✅ `backend/app/db.py` (engine SQLAlchemy + get_db dépendance FastAPI) + `backend/app/models/base.py` (Base déclarative) + test connexion
- C3 ✅ Alembic initialisé (`alembic.ini` + `alembic/env.py` personnalisé pour charger l'URL depuis pydantic-settings)
- C4 ✅ Migration vide initiale créée (révision `9b47b41a827e`), puis enrichie en D avec toutes les tables
- C5 ✅ `conftest.py` — fixtures pytest `test_engine` (avec `alembic upgrade head` sur DB `_test`) et `db_session` (rollback auto)

### Section D — Modèles ORM ✅

**Commits** : 2 (feat + style)

- D1 ✅ `User` (email, password_hash, role enum `UserRole` StrEnum, full_name, is_active, timestamps, last_login_at)
- D2 ✅ `Entity` (name, legal_name, siret, parent_entity_id self-FK) + `validate_entity_tree()` avec détection de cycles
- D3 ✅ `UserEntityAccess` (table de liaison user ↔ entity avec UniqueConstraint)
- D4 ✅ `BankAccount` (entity_id FK, iban unique, bic, bank_name, bank_code, currency, is_active)
- **Migration consolidée** : au lieu de 4 migrations séparées (plan original), 1 seule migration `9b47b41a827e_initial_schema_placeholder.py` crée toutes les tables. Plus propre et plus simple à gérer pour la suite.
- **Tests** : 1 fichier par modèle, couvre les cas nominaux + contraintes d'unicité + détection de cycles.

## ⚠️ À valider par l'utilisateur avant de lancer Section E

```bash
# 1. Démarrer Docker Desktop
# 2. Démarrer la DB dev
cd "C:\Users\trist\Documents\Outil\Clone AGICAP"
docker compose -f docker-compose.dev.yml up -d db

# 3. Activer le venv et appliquer la migration sur la DB dev
cd backend
.venv\Scripts\activate
alembic upgrade head

# 4. Lancer tous les tests
pytest -v
```

**Résultat attendu** : ~12 tests passent (3 de B + 2 de C + 7 de D). Si KO, envoyer l'erreur à l'assistant avant Section E.

## Reprise de session

**Pour reprendre** : dis à l'assistant :

> "Reprends Plan 0 à la Section E. Les tests locaux passent."

L'assistant lira `PROGRESS.md` + `git log` et enchaînera sur **E1 (hashage Argon2)**.
