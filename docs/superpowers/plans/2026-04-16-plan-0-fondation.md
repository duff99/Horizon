# Plan 0 — Fondation : Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mettre en place le socle technique du projet : structure du dépôt, base de données avec les entités métier fondamentales (utilisateurs, sociétés, comptes bancaires), authentification sécurisée, CRUD administratifs, squelette frontend React avec page de connexion et layout, stack Docker fonctionnelle en local.

**Architecture:** Monolithe modulaire Python/FastAPI côté backend, React/TypeScript côté frontend, PostgreSQL comme base, Caddy en reverse proxy, tout orchestré par Docker Compose. Aucune logique métier complexe dans ce plan : uniquement les fondations sur lesquelles les plans 1 à 6 viendront brancher les fonctionnalités (import, catégorisation, tableau de bord, prévisionnel, alertes, production).

**Tech Stack:**

- **Backend** : Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, argon2-cffi, pydantic v2, python-jose (JWT si besoin — privilégie les cookies de session), slowapi (rate limiting), pytest + pytest-asyncio
- **Frontend** : React 18, TypeScript 5, Vite 5, Tailwind CSS 3, shadcn/ui, TanStack Query 5, React Hook Form, Zod, Vitest + Testing Library
- **Infra** : PostgreSQL 16, Docker + Docker Compose, Caddy 2

---

## Prérequis avant de commencer

- Docker Desktop installé et fonctionnel (`docker --version` → ≥ 24)
- Git installé (`git --version`)
- Python 3.12 installé en local (`python --version` → 3.12.x)
- Node.js 20+ installé en local (`node --version` → ≥ v20)
- Le dépôt est déjà initialisé à `C:\Users\trist\Documents\Outil\Clone AGICAP` avec la spec committée (`docs/superpowers/specs/2026-04-16-clone-agicap-design.md`)
- **Compétences supposées du développeur** : bon niveau Python/TypeScript général, peu ou pas d'expérience sur FastAPI / SQLAlchemy 2.x / shadcn-ui. Le plan explicite toutes les commandes et tous les extraits de code critiques.

---

## Conventions globales du projet

- **Nommage** : tout en `snake_case` côté Python, `camelCase` côté TypeScript. Les tables DB en `snake_case`, pluriel (ex. `bank_accounts`).
- **Interface utilisateur** : **100 % en français**. Code source (noms de variables, commentaires techniques internes) peut rester en anglais. Messages utilisateur, libellés, erreurs remontées à l'UI → français.
- **Gestion des dates** : toujours en UTC côté backend, conversion en local côté frontend.
- **Tests avant code (TDD strict)** : chaque nouvelle fonctionnalité commence par un test qui échoue, puis l'implémentation minimale pour le faire passer. Voir skill `@superpowers:test-driven-development`.
- **Commits fréquents** : 1 commit = 1 changement atomique et cohérent. Messages de commit en anglais, format Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`, `chore:`, `docs:`).

---

## Structure du dépôt (cible à la fin du Plan 0)

```
Clone AGICAP/
├── .gitignore
├── .env.example
├── README.md
├── docker-compose.yml
├── docker-compose.dev.yml
├── Caddyfile
│
├── backend/
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── .env.example
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── <timestamp>_initial_schema.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # point d'entrée FastAPI
│   │   ├── config.py                 # paramètres via pydantic-settings
│   │   ├── db.py                     # engine + Session
│   │   ├── deps.py                   # dépendances FastAPI (auth, session)
│   │   ├── security.py               # hashage Argon2, tokens de session
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # Base déclarative
│   │   │   ├── user.py
│   │   │   ├── entity.py
│   │   │   ├── user_entity_access.py
│   │   │   └── bank_account.py
│   │   ├── schemas/                  # DTOs pydantic
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── user.py
│   │   │   ├── entity.py
│   │   │   └── bank_account.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── router.py             # agrégateur
│   │   │   ├── auth.py
│   │   │   ├── me.py
│   │   │   ├── users.py
│   │   │   ├── entities.py
│   │   │   ├── bank_accounts.py
│   │   │   └── health.py
│   │   └── errors.py                 # exceptions métier
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py               # fixtures pytest (DB test, client, etc.)
│       ├── test_health.py
│       ├── test_security.py
│       ├── test_auth.py
│       ├── test_users_api.py
│       ├── test_entities_api.py
│       └── test_bank_accounts_api.py
│
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   ├── components.json               # config shadcn
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── index.html
│   ├── public/
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── router.tsx
│       ├── api/
│       │   ├── client.ts             # fetch wrapper
│       │   ├── auth.ts
│       │   ├── users.ts
│       │   ├── entities.ts
│       │   └── bankAccounts.ts
│       ├── types/
│       │   └── api.ts
│       ├── hooks/
│       │   └── useAuth.ts
│       ├── components/
│       │   ├── ui/                   # composants shadcn
│       │   ├── Layout.tsx
│       │   ├── Sidebar.tsx
│       │   ├── EntitySelector.tsx
│       │   └── ProtectedRoute.tsx
│       ├── pages/
│       │   ├── LoginPage.tsx
│       │   ├── DashboardPage.tsx     # placeholder
│       │   ├── AdminUsersPage.tsx
│       │   ├── AdminEntitiesPage.tsx
│       │   └── AdminBankAccountsPage.tsx
│       └── test/
│           ├── setup.ts
│           └── LoginPage.test.tsx
│
└── docs/
    ├── operations/
    │   └── local-dev.md              # doc d'exécution locale
    └── superpowers/
        ├── specs/
        │   └── 2026-04-16-clone-agicap-design.md
        └── plans/
            └── 2026-04-16-plan-0-fondation.md    # ce fichier
```

**Rationale de la structure :**

- Backend et frontend sont deux dossiers totalement isolés (deux images Docker séparées, deux écosystèmes d'outils). Cela permet de les faire évoluer indépendamment et de paralléliser le développement.
- Les modèles SQLAlchemy sont **un fichier par modèle** (pas un gros `models.py`), pour éviter les fichiers qui grossissent indéfiniment à mesure que les plans suivants ajoutent des tables.
- Les routes API sont **un fichier par ressource**, agrégées dans `api/router.py`.
- Les schémas Pydantic (DTOs) sont séparés des modèles SQLAlchemy : cela découple la représentation DB de la représentation API.
- Les tests suivent la structure du code et sont tous dans `backend/tests/` pour que pytest les trouve d'un coup.

---

## Sections du plan

Le plan est découpé en **10 sections** :

- **A** — Initialisation du dépôt et squelette (5 tâches)
- **B** — Environnement Python et outils qualité (4 tâches)
- **C** — Base de données : PostgreSQL en Docker dev + SQLAlchemy + Alembic (5 tâches)
- **D** — Modèles ORM : User, Entity, UserEntityAccess, BankAccount (4 tâches)
- **E** — Sécurité : hashage Argon2, sessions, rate limiting (5 tâches)
- **F** — API : Auth + /me + Admin CRUD (6 tâches)
- **G** — Santé et observabilité de base : /healthz, /readyz (2 tâches)
- **H** — Frontend : squelette Vite + React + Tailwind + shadcn (5 tâches)
- **I** — Frontend : authentification, layout, admin pages (6 tâches)
- **J** — Orchestration Docker : docker-compose.yml complet + Caddy + test end-to-end (4 tâches)

**Total : ~46 tâches numérotées**, chacune découpée en 3-5 étapes (TDD cycle). Estimation : 5 à 7 jours de développement effectif.

---

# SECTION A — Initialisation du dépôt

### Tâche A1 : Créer `.gitignore` et `README.md` à la racine

**Files:**
- Create: `C:\Users\trist\Documents\Outil\Clone AGICAP\.gitignore`
- Create: `C:\Users\trist\Documents\Outil\Clone AGICAP\README.md`

- [ ] **Étape 1 : Créer le `.gitignore`**

```gitignore
# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/
.venv/
venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/
htmlcov/
.coverage

# Node
node_modules/
dist/
build/
*.log

# IDE
.idea/
.vscode/
*.swp

# OS
.DS_Store
Thumbs.db

# Secrets et données locales
.env
.env.local
backend/.env
frontend/.env

# Data / backups (ne JAMAIS commiter)
/data/
/backups/
*.sql
*.sql.gpg
*.dump

# Tests
.tox/
.nox/

# Docker
docker-compose.override.yml
```

- [ ] **Étape 2 : Créer le `README.md`**

```markdown
# Clone Agicap — Outil de gestion de trésorerie

Outil de suivi et prévisionnel de trésorerie auto-hébergé, inspiré d'Agicap.
Import manuel de relevés bancaires PDF, multi-entités (holding + filiales),
multi-utilisateurs.

## Documentation

- **Spécification** : [docs/superpowers/specs/2026-04-16-clone-agicap-design.md](docs/superpowers/specs/2026-04-16-clone-agicap-design.md)
- **Plan 0 — Fondation** : [docs/superpowers/plans/2026-04-16-plan-0-fondation.md](docs/superpowers/plans/2026-04-16-plan-0-fondation.md)
- **Développement local** : [docs/operations/local-dev.md](docs/operations/local-dev.md)

## Démarrage rapide (dev)

```bash
cp .env.example .env
docker compose -f docker-compose.dev.yml up -d
# Backend API : http://localhost:8000
# Frontend   : http://localhost:5173
```

## Stack

Python 3.12 + FastAPI + SQLAlchemy + PostgreSQL 16 + React 18 + TypeScript + Vite + Tailwind + Docker + Caddy.

## Licence

Propriétaire — utilisation interne uniquement.
```

- [ ] **Étape 3 : Commit**

```bash
cd "C:/Users/trist/Documents/Outil/Clone AGICAP"
git add .gitignore README.md
git commit -m "chore: add gitignore and project readme"
```

---

### Tâche A2 : Créer la structure des dossiers racine

**Files:**
- Create: `backend/` (vide pour l'instant)
- Create: `frontend/` (vide)
- Create: `docs/operations/` (vide)

- [ ] **Étape 1 : Créer les dossiers**

```bash
cd "C:/Users/trist/Documents/Outil/Clone AGICAP"
mkdir -p backend frontend docs/operations
```

- [ ] **Étape 2 : Créer des `.gitkeep` pour que Git suive les dossiers vides**

```bash
touch backend/.gitkeep frontend/.gitkeep docs/operations/.gitkeep
```

- [ ] **Étape 3 : Commit**

```bash
git add backend/ frontend/ docs/
git commit -m "chore: create top-level directory structure"
```

---

### Tâche A3 : Créer `.env.example` à la racine

**Files:**
- Create: `.env.example`

- [ ] **Étape 1 : Créer le fichier `.env.example`**

```env
# Domaine public (HTTPS en prod, localhost en dev)
APP_DOMAIN=localhost
ADMIN_EMAIL=admin@example.com

# Postgres
POSTGRES_USER=tresorerie
POSTGRES_PASSWORD=change_me_in_production
POSTGRES_DB=tresorerie

# Backend
BACKEND_SECRET_KEY=change_me_generate_a_random_32byte_string
BACKEND_SESSION_HOURS=8
BACKEND_CORS_ORIGINS=http://localhost:5173

# Frontend
VITE_API_BASE_URL=http://localhost:8000

# Caddy (prod uniquement)
CADDY_EMAIL=admin@example.com
```

- [ ] **Étape 2 : Commit**

```bash
git add .env.example
git commit -m "chore: add environment variables template"
```

---

### Tâche A4 : Créer la doc de dev local

**Files:**
- Create: `docs/operations/local-dev.md`

- [ ] **Étape 1 : Créer le fichier**

````markdown
# Développement local

## Première mise en route

1. Copier la configuration :
   ```bash
   cp .env.example .env
   ```
2. Démarrer la base Postgres en Docker :
   ```bash
   docker compose -f docker-compose.dev.yml up -d db
   ```
3. Backend :
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # (ou .venv\Scripts\activate sous Windows PowerShell)
   pip install -e ".[dev]"
   alembic upgrade head
   uvicorn app.main:app --reload --port 8000
   ```
4. Frontend :
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

- Backend API : http://localhost:8000 (doc Swagger à `/docs`)
- Frontend    : http://localhost:5173

## Tests

- Backend : `cd backend && pytest`
- Frontend : `cd frontend && npm test`

## Création du premier admin

Après le premier `alembic upgrade head`, la page d'accueil frontend propose
de créer le premier compte admin. C'est l'amorçage initial (voir plan 0 §F).
````

- [ ] **Étape 2 : Commit**

```bash
git add docs/operations/local-dev.md
git commit -m "docs: add local development setup guide"
```

---

### Tâche A5 : Supprimer les `.gitkeep` devenus inutiles (quand les vrais fichiers arriveront)

Cette tâche est un rappel pour plus tard. À la fin du plan 0, les dossiers auront du contenu réel ; on supprimera les `.gitkeep` dans le dernier commit.

- [ ] **Note pour l'exécution** : cette tâche est regroupée au commit final de la section J.

---

# SECTION B — Environnement Python et outils qualité

### Tâche B1 : Créer `backend/pyproject.toml` avec les dépendances

**Files:**
- Create: `backend/pyproject.toml`

- [ ] **Étape 1 : Écrire le `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "tresorerie-backend"
version = "0.1.0"
description = "Backend de l'outil de gestion de trésorerie"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.110,<1",
    "uvicorn[standard]>=0.29,<1",
    "sqlalchemy>=2.0,<3",
    "psycopg[binary]>=3.1,<4",
    "alembic>=1.13,<2",
    "pydantic>=2.6,<3",
    "pydantic-settings>=2.2,<3",
    "argon2-cffi>=23.1,<24",
    "python-multipart>=0.0.9",
    "email-validator>=2.1,<3",
    "slowapi>=0.1.9,<1",
    "itsdangerous>=2.1,<3",
]

[project.optional-dependencies]
dev = [
    "pytest>=8,<9",
    "pytest-asyncio>=0.23,<1",
    "pytest-cov>=4.1,<5",
    "httpx>=0.27,<1",
    "ruff>=0.4,<1",
    "mypy>=1.10,<2",
    "types-python-jose",
]

[tool.hatch.build.targets.wheel]
packages = ["app"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM"]
ignore = []

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-v --strict-markers --cov=app --cov-report=term-missing"

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]
```

- [ ] **Étape 2 : Créer un venv local et installer**

```bash
cd backend
python -m venv .venv
# Sous Windows PowerShell :
.venv\Scripts\activate
# Sous Bash/WSL :
# source .venv/bin/activate
pip install -e ".[dev]"
```

- [ ] **Étape 3 : Commit**

```bash
cd ..
git add backend/pyproject.toml
git commit -m "feat(backend): initial pyproject with fastapi stack"
```

---

### Tâche B2 : Créer `backend/app/main.py` minimal (test "Hello")

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_health_basic.py`

- [ ] **Étape 1 : Écrire le test d'abord (TDD)**

`backend/tests/test_health_basic.py` :

```python
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root_returns_200() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "name": "tresorerie-backend"}
```

- [ ] **Étape 2 : Créer les fichiers vides `__init__.py`**

```bash
touch backend/app/__init__.py backend/tests/__init__.py
```

- [ ] **Étape 3 : Créer `conftest.py` vide pour l'instant**

```python
# backend/tests/conftest.py
# Fixtures pytest — enrichies dans les sections suivantes
```

- [ ] **Étape 4 : Lancer le test, vérifier qu'il échoue**

```bash
cd backend
pytest tests/test_health_basic.py -v
```
Sortie attendue : `ModuleNotFoundError: No module named 'app.main'` (ou équivalent).

- [ ] **Étape 5 : Implémenter `app/main.py` minimal pour faire passer le test**

```python
# backend/app/main.py
from fastapi import FastAPI

app = FastAPI(
    title="Outil de trésorerie",
    description="API de l'outil de gestion de trésorerie auto-hébergé",
    version="0.1.0",
)


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "name": "tresorerie-backend"}
```

- [ ] **Étape 6 : Relancer le test**

```bash
pytest tests/test_health_basic.py -v
```
Sortie attendue : `PASSED`.

- [ ] **Étape 7 : Commit**

```bash
cd ..
git add backend/app backend/tests
git commit -m "feat(backend): minimal FastAPI app with root endpoint"
```

---

### Tâche B3 : Configurer ruff et mypy, passer les checks

**Files:**
- Modify: `backend/pyproject.toml` (déjà OK)

- [ ] **Étape 1 : Lancer ruff**

```bash
cd backend
ruff check .
ruff format --check .
```
Corriger tout problème signalé (il ne devrait pas y en avoir avec le code fourni).

- [ ] **Étape 2 : Lancer mypy**

```bash
mypy app
```
Corriger tout problème signalé.

- [ ] **Étape 3 : Ajouter un script de vérification commode**

Créer `backend/scripts/check.sh` :

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
ruff check .
ruff format --check .
mypy app
pytest
```

Rendre exécutable (sous Unix) : `chmod +x backend/scripts/check.sh`.

Sous Windows, créer aussi `backend/scripts/check.ps1` :

```powershell
Set-Location $PSScriptRoot\..
ruff check .
ruff format --check .
mypy app
pytest
```

- [ ] **Étape 4 : Commit**

```bash
cd ..
git add backend/scripts
git commit -m "chore(backend): add check script for CI-like local validation"
```

---

### Tâche B4 : Configurer pydantic-settings pour les variables d'environnement

**Files:**
- Create: `backend/app/config.py`
- Create: `backend/tests/test_config.py`

- [ ] **Étape 1 : Écrire le test d'abord**

`backend/tests/test_config.py` :

```python
import os

import pytest

from app.config import Settings


def test_settings_loads_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost/x")
    monkeypatch.setenv("BACKEND_SECRET_KEY", "a" * 32)
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", "http://localhost:5173")

    settings = Settings()  # type: ignore[call-arg]

    assert settings.database_url == "postgresql+psycopg://u:p@localhost/x"
    assert settings.secret_key == "a" * 32
    assert settings.cors_origins == ["http://localhost:5173"]


def test_settings_rejects_short_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost/x")
    monkeypatch.setenv("BACKEND_SECRET_KEY", "too_short")
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", "http://localhost:5173")

    with pytest.raises(ValueError, match="32 caractères"):
        Settings()  # type: ignore[call-arg]
```

- [ ] **Étape 2 : Vérifier que le test échoue**

```bash
pytest tests/test_config.py -v
```
Sortie attendue : erreur d'import.

- [ ] **Étape 3 : Implémenter `app/config.py`**

```python
# backend/app/config.py
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = Field(..., alias="DATABASE_URL")
    secret_key: str = Field(..., alias="BACKEND_SECRET_KEY")
    session_hours: int = Field(8, alias="BACKEND_SESSION_HOURS")
    cors_origins_raw: str = Field(..., alias="BACKEND_CORS_ORIGINS")

    @field_validator("secret_key")
    @classmethod
    def _secret_long_enough(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("BACKEND_SECRET_KEY doit contenir au moins 32 caractères")
        return v

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]


def get_settings() -> Settings:
    """Point d'accès paresseux (testable)."""
    return Settings()  # type: ignore[call-arg]
```

- [ ] **Étape 4 : Relancer le test, vérifier le succès**

```bash
pytest tests/test_config.py -v
```
Sortie attendue : les deux tests PASS.

- [ ] **Étape 5 : Créer `backend/.env.example`**

```env
DATABASE_URL=postgresql+psycopg://tresorerie:change_me@localhost:5432/tresorerie
BACKEND_SECRET_KEY=replace_with_32_plus_random_characters_xxxxxx
BACKEND_SESSION_HOURS=8
BACKEND_CORS_ORIGINS=http://localhost:5173
```

- [ ] **Étape 6 : Commit**

```bash
cd ..
git add backend/app/config.py backend/tests/test_config.py backend/.env.example
git commit -m "feat(backend): settings via pydantic-settings with validation"
```

---

# SECTION C — Base de données : PostgreSQL + SQLAlchemy + Alembic

### Tâche C1 : Créer `docker-compose.dev.yml` avec service Postgres uniquement

**Files:**
- Create: `docker-compose.dev.yml` (à la racine du dépôt)

- [ ] **Étape 1 : Créer le fichier**

```yaml
# docker-compose.dev.yml
# Services minimaux pour développement local : DB uniquement.
# Backend et frontend tournent hors Docker en dev (avec hot reload).
version: "3.9"

services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-tresorerie}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-change_me_in_production}
      POSTGRES_DB: ${POSTGRES_DB:-tresorerie}
    ports:
      - "5432:5432"
    volumes:
      - pg_data_dev:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-tresorerie}"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  pg_data_dev:
```

- [ ] **Étape 2 : Démarrer la DB**

```bash
cd "C:/Users/trist/Documents/Outil/Clone AGICAP"
cp .env.example .env
docker compose -f docker-compose.dev.yml up -d db
docker compose -f docker-compose.dev.yml ps
```
Vérifier : `db` doit être `healthy` après quelques secondes.

- [ ] **Étape 3 : Commit**

```bash
git add docker-compose.dev.yml
git commit -m "chore: add dev docker-compose with postgres"
```

---

### Tâche C2 : Configurer l'engine SQLAlchemy

**Files:**
- Create: `backend/app/db.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/base.py`
- Create: `backend/tests/test_db_connection.py`

- [ ] **Étape 1 : Créer le test (vérifie qu'on peut se connecter)**

`backend/tests/test_db_connection.py` :

```python
from sqlalchemy import text

from app.db import get_engine


def test_engine_connects() -> None:
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar_one()
    assert result == 1
```

- [ ] **Étape 2 : Créer la base déclarative**

`backend/app/models/base.py` :

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base déclarative commune à tous les modèles ORM."""
```

`backend/app/models/__init__.py` :

```python
from app.models.base import Base

__all__ = ["Base"]
```

- [ ] **Étape 3 : Créer `app/db.py`**

```python
# backend/app/db.py
from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(settings.database_url, pool_pre_ping=True, future=True)


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False, autoflush=False)


def get_db() -> Iterator[Session]:
    """Dépendance FastAPI : ouvre / ferme une session par requête."""
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
```

- [ ] **Étape 4 : Lancer le test**

Assurer que la DB dev tourne (`docker compose -f docker-compose.dev.yml ps`), puis :

```bash
cd backend
# Export DATABASE_URL pour le test (ou créer un .env local)
pytest tests/test_db_connection.py -v
```
Sortie attendue : PASS.

- [ ] **Étape 5 : Commit**

```bash
cd ..
git add backend/app/db.py backend/app/models/ backend/tests/test_db_connection.py
git commit -m "feat(backend): sqlalchemy engine and declarative base"
```

---

### Tâche C3 : Initialiser Alembic

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/.gitkeep`

- [ ] **Étape 1 : Initialiser Alembic**

```bash
cd backend
alembic init alembic
```
Cela crée `alembic.ini` et le dossier `alembic/`.

- [ ] **Étape 2 : Éditer `alembic/env.py`**

Remplacer **tout le contenu** de `backend/alembic/env.py` par :

```python
from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import get_settings
from app.models import Base  # noqa: F401 — import side effects

# Importer tous les modèles ici pour qu'Alembic les voie.
# Au fur et à mesure qu'on ajoute des modèles, on les importe ci-dessous.

config = context.config

# Surcharger l'URL depuis nos settings (ne pas utiliser alembic.ini)
config.set_main_option("sqlalchemy.url", get_settings().database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Étape 3 : Éditer `alembic.ini`**

Dans `backend/alembic.ini`, chercher la ligne `sqlalchemy.url = ...` et la remplacer par (commentaire uniquement — on utilise `env.py`) :

```ini
# sqlalchemy.url: overridden by app.config in env.py
sqlalchemy.url =
```

- [ ] **Étape 4 : Vérifier que `alembic current` répond**

```bash
cd backend
alembic current
```
Sortie attendue : rien (aucune migration appliquée), mais pas d'erreur.

- [ ] **Étape 5 : Commit**

```bash
cd ..
git add backend/alembic.ini backend/alembic/
git commit -m "chore(backend): initialize alembic"
```

---

### Tâche C4 : Créer la migration initiale vide et la tester

**Files:**
- Create: `backend/alembic/versions/<timestamp>_initial_schema.py` (généré)

- [ ] **Étape 1 : Générer une migration vide**

```bash
cd backend
alembic revision -m "initial schema placeholder"
```

- [ ] **Étape 2 : Vérifier le fichier généré**

Ouvrir le fichier dans `backend/alembic/versions/`. Les fonctions `upgrade()` et `downgrade()` doivent être vides (juste `pass`). On les enrichira avec les vrais modèles à la tâche D.

- [ ] **Étape 3 : Appliquer et vérifier**

```bash
alembic upgrade head
alembic current
```
Sortie attendue : la version du fichier généré apparaît.

- [ ] **Étape 4 : Commit (même si la migration est vide)**

```bash
cd ..
git add backend/alembic/versions/
git commit -m "feat(backend): empty initial alembic migration"
```

---

### Tâche C5 : Fixture pytest pour une base de données de test isolée

**Files:**
- Modify: `backend/tests/conftest.py`

- [ ] **Étape 1 : Mettre à jour `conftest.py`**

```python
# backend/tests/conftest.py
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models import Base


@pytest.fixture(scope="session")
def test_database_url() -> str:
    """URL pointant sur une base de test séparée de la base de dev.

    Par convention, on suffixe `_test` à la base principale.
    """
    base = get_settings().database_url
    # Remplace le dernier segment "/nom_base" par "/nom_base_test"
    if "/" not in base:
        raise RuntimeError("DATABASE_URL malformée")
    head, _, name = base.rpartition("/")
    return f"{head}/{name}_test"


@pytest.fixture(scope="session")
def test_engine(test_database_url: str) -> Iterator[Engine]:
    """Crée un engine vers la base de test et prépare les tables."""
    engine = create_engine(test_database_url, future=True)
    # Crée la base si absente (Postgres ne le fait pas tout seul)
    from sqlalchemy import text
    from sqlalchemy.engine.url import make_url

    url = make_url(test_database_url)
    admin_url = url.set(database="postgres")
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT", future=True)
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :n"),
            {"n": url.database},
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin_engine.dispose()

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db_session(test_engine: Engine) -> Iterator[Session]:
    """Session de test avec rollback automatique à la fin."""
    connection = test_engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
```

- [ ] **Étape 2 : Vérifier que ça n'a rien cassé**

```bash
cd backend
pytest -v
```
Sortie attendue : les tests existants passent toujours.

- [ ] **Étape 3 : Commit**

```bash
cd ..
git add backend/tests/conftest.py
git commit -m "test(backend): add isolated test-db fixtures"
```

---

# SECTION D — Modèles ORM

### Tâche D1 : Modèle `User`

**Files:**
- Create: `backend/app/models/user.py`
- Modify: `backend/alembic/env.py` (importer le nouveau modèle)
- Create: `backend/tests/test_model_user.py`
- Nouvelle migration Alembic

- [ ] **Étape 1 : Écrire le test d'abord**

`backend/tests/test_model_user.py` :

```python
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.user import User, UserRole


def test_create_user(db_session: Session) -> None:
    user = User(
        email="admin@test.local",
        password_hash="fakehash",
        role=UserRole.ADMIN,
        full_name="Admin Test",
    )
    db_session.add(user)
    db_session.commit()

    assert user.id is not None
    assert user.is_active is True
    assert user.created_at is not None
    assert user.created_at.tzinfo == UTC


def test_email_is_unique(db_session: Session) -> None:
    import pytest
    from sqlalchemy.exc import IntegrityError

    u1 = User(email="a@b.com", password_hash="x", role=UserRole.READER)
    db_session.add(u1)
    db_session.commit()

    u2 = User(email="a@b.com", password_hash="y", role=UserRole.READER)
    db_session.add(u2)
    with pytest.raises(IntegrityError):
        db_session.commit()
```

- [ ] **Étape 2 : Créer le modèle**

`backend/app/models/user.py` :

```python
from __future__ import annotations

import enum
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    READER = "reader"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), nullable=False, default=UserRole.READER
    )
    full_name: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

- [ ] **Étape 3 : Importer dans `app/models/__init__.py` et dans `alembic/env.py`**

`backend/app/models/__init__.py` :

```python
from app.models.base import Base
from app.models.user import User, UserRole

__all__ = ["Base", "User", "UserRole"]
```

(L'import dans `alembic/env.py` est déjà fait via `from app.models import Base` — l'ajout d'un modèle ré-exporté suffit.)

- [ ] **Étape 4 : Générer la migration avec `--autogenerate`**

```bash
cd backend
alembic revision --autogenerate -m "add users table"
```
Inspecter le fichier généré dans `alembic/versions/` : il doit contenir `op.create_table("users", ...)`.

- [ ] **Étape 5 : Appliquer et tester**

```bash
alembic upgrade head
pytest tests/test_model_user.py -v
```
Sortie attendue : tests PASS.

- [ ] **Étape 6 : Commit**

```bash
cd ..
git add backend/app/models/user.py backend/app/models/__init__.py backend/alembic/versions/ backend/tests/test_model_user.py
git commit -m "feat(backend): add User model and migration"
```

---

### Tâche D2 : Modèle `Entity` (arborescence holding/filiales)

**Files:**
- Create: `backend/app/models/entity.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/tests/test_model_entity.py`

- [ ] **Étape 1 : Test TDD**

`backend/tests/test_model_entity.py` :

```python
from sqlalchemy.orm import Session

from app.models.entity import Entity


def test_entity_without_parent(db_session: Session) -> None:
    holding = Entity(name="Holding", legal_name="HOLDING SARL", parent_entity_id=None)
    db_session.add(holding)
    db_session.commit()
    assert holding.id is not None
    assert holding.parent_entity_id is None


def test_entity_with_parent(db_session: Session) -> None:
    holding = Entity(name="Holding", legal_name="HOLDING SARL")
    db_session.add(holding)
    db_session.flush()

    filiale = Entity(name="Filiale 1", legal_name="FIL 1 SAS", parent_entity_id=holding.id)
    db_session.add(filiale)
    db_session.commit()

    assert filiale.parent_entity_id == holding.id


def test_entity_self_reference_forbidden(db_session: Session) -> None:
    """Un noeud ne peut pas être son propre parent (invariant applicatif)."""
    import pytest
    from app.models.entity import validate_entity_tree

    e = Entity(name="X", legal_name="X", id=1, parent_entity_id=1)
    with pytest.raises(ValueError, match="ne peut pas être son propre parent"):
        validate_entity_tree(e)
```

- [ ] **Étape 2 : Créer le modèle**

`backend/app/models/entity.py` :

```python
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    siret: Mapped[str | None] = mapped_column(String(32))
    parent_entity_id: Mapped[int | None] = mapped_column(
        ForeignKey("entities.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


def validate_entity_tree(entity: Entity) -> None:
    """Validation applicative : pas de self-reference (complément au schéma)."""
    if entity.id is not None and entity.parent_entity_id == entity.id:
        raise ValueError("Une société ne peut pas être son propre parent")
```

- [ ] **Étape 3 : Exporter dans `__init__.py`**

```python
# backend/app/models/__init__.py
from app.models.base import Base
from app.models.entity import Entity
from app.models.user import User, UserRole

__all__ = ["Base", "Entity", "User", "UserRole"]
```

- [ ] **Étape 4 : Migration Alembic**

```bash
cd backend
alembic revision --autogenerate -m "add entities table"
alembic upgrade head
```

- [ ] **Étape 5 : Lancer les tests**

```bash
pytest tests/test_model_entity.py -v
```

- [ ] **Étape 6 : Commit**

```bash
cd ..
git add backend/app/models/entity.py backend/app/models/__init__.py backend/alembic/versions/ backend/tests/test_model_entity.py
git commit -m "feat(backend): add Entity model with parent hierarchy"
```

---

### Tâche D3 : Modèle `UserEntityAccess` (table de liaison N-N)

**Files:**
- Create: `backend/app/models/user_entity_access.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/tests/test_model_user_entity_access.py`

- [ ] **Étape 1 : Test TDD**

`backend/tests/test_model_user_entity_access.py` :

```python
from sqlalchemy.orm import Session

from app.models.entity import Entity
from app.models.user import User, UserRole
from app.models.user_entity_access import UserEntityAccess


def test_link_user_to_entity(db_session: Session) -> None:
    user = User(email="u@x.com", password_hash="h", role=UserRole.READER)
    entity = Entity(name="E", legal_name="E SARL")
    db_session.add_all([user, entity])
    db_session.flush()

    link = UserEntityAccess(user_id=user.id, entity_id=entity.id)
    db_session.add(link)
    db_session.commit()

    assert link.user_id == user.id
    assert link.entity_id == entity.id


def test_uniqueness(db_session: Session) -> None:
    import pytest
    from sqlalchemy.exc import IntegrityError

    user = User(email="x@y.com", password_hash="h", role=UserRole.READER)
    entity = Entity(name="E2", legal_name="E2 SARL")
    db_session.add_all([user, entity])
    db_session.flush()

    db_session.add(UserEntityAccess(user_id=user.id, entity_id=entity.id))
    db_session.commit()

    db_session.add(UserEntityAccess(user_id=user.id, entity_id=entity.id))
    with pytest.raises(IntegrityError):
        db_session.commit()
```

- [ ] **Étape 2 : Créer le modèle**

`backend/app/models/user_entity_access.py` :

```python
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserEntityAccess(Base):
    __tablename__ = "user_entity_access"
    __table_args__ = (UniqueConstraint("user_id", "entity_id", name="uq_user_entity"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
```

- [ ] **Étape 3 : Exporter, migrer, tester, commit (même processus que D1/D2)**

```python
# __init__.py mis à jour
from app.models.user_entity_access import UserEntityAccess
```

```bash
cd backend
alembic revision --autogenerate -m "add user_entity_access table"
alembic upgrade head
pytest tests/test_model_user_entity_access.py -v
cd ..
git add backend/app/models/user_entity_access.py backend/app/models/__init__.py backend/alembic/versions/ backend/tests/test_model_user_entity_access.py
git commit -m "feat(backend): add UserEntityAccess join model"
```

---

### Tâche D4 : Modèle `BankAccount`

**Files:**
- Create: `backend/app/models/bank_account.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/tests/test_model_bank_account.py`

- [ ] **Étape 1 : Test TDD**

`backend/tests/test_model_bank_account.py` :

```python
from sqlalchemy.orm import Session

from app.models.bank_account import BankAccount
from app.models.entity import Entity


def test_create_bank_account(db_session: Session) -> None:
    e = Entity(name="Filiale", legal_name="FIL SAS")
    db_session.add(e)
    db_session.flush()

    ba = BankAccount(
        entity_id=e.id,
        name="Compte pro Delubac",
        iban="FR7612879000011117020200105",
        bank_name="Delubac",
        bank_code="delubac",
        currency="EUR",
    )
    db_session.add(ba)
    db_session.commit()
    assert ba.id is not None
    assert ba.is_active is True


def test_iban_unique(db_session: Session) -> None:
    import pytest
    from sqlalchemy.exc import IntegrityError

    e = Entity(name="E3", legal_name="E3 SAS")
    db_session.add(e)
    db_session.flush()

    db_session.add(
        BankAccount(
            entity_id=e.id,
            name="A",
            iban="FR7612879000011117020200105",
            bank_name="Delubac",
            bank_code="delubac",
        )
    )
    db_session.commit()

    db_session.add(
        BankAccount(
            entity_id=e.id,
            name="B",
            iban="FR7612879000011117020200105",
            bank_name="Delubac",
            bank_code="delubac",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
```

- [ ] **Étape 2 : Créer le modèle**

`backend/app/models/bank_account.py` :

```python
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    iban: Mapped[str] = mapped_column(String(34), unique=True, nullable=False)
    bic: Mapped[str | None] = mapped_column(String(11))
    bank_name: Mapped[str] = mapped_column(String(255), nullable=False)
    bank_code: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Code interne : 'delubac', 'qonto', etc."
    )
    account_number: Mapped[str | None] = mapped_column(String(34))
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
```

- [ ] **Étape 3 : Exporter, migrer, tester, commit**

```python
# __init__.py mis à jour
from app.models.bank_account import BankAccount
```

```bash
cd backend
alembic revision --autogenerate -m "add bank_accounts table"
alembic upgrade head
pytest tests/test_model_bank_account.py -v
cd ..
git add backend/app/models/bank_account.py backend/app/models/__init__.py backend/alembic/versions/ backend/tests/test_model_bank_account.py
git commit -m "feat(backend): add BankAccount model"
```

---

# SECTION E — Sécurité : hashage, sessions, rate limiting

### Tâche E1 : Hashage Argon2

**Files:**
- Create: `backend/app/security.py`
- Create: `backend/tests/test_security.py`

- [ ] **Étape 1 : Test TDD**

`backend/tests/test_security.py` :

```python
from app.security import hash_password, verify_password


def test_hash_verify_roundtrip() -> None:
    raw = "correct horse battery staple"
    h = hash_password(raw)
    assert h != raw
    assert verify_password(raw, h) is True
    assert verify_password("wrong", h) is False


def test_hash_is_unique_per_call() -> None:
    raw = "same_password"
    assert hash_password(raw) != hash_password(raw)
```

- [ ] **Étape 2 : Implémenter**

`backend/app/security.py` :

```python
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(raw: str) -> str:
    return _hasher.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    try:
        _hasher.verify(hashed, raw)
        return True
    except VerifyMismatchError:
        return False
```

- [ ] **Étape 3 : Test + commit**

```bash
cd backend
pytest tests/test_security.py -v
cd ..
git add backend/app/security.py backend/tests/test_security.py
git commit -m "feat(backend): argon2 password hashing"
```

---

### Tâche E2 : Politique de mot de passe (longueur minimale + HIBP local)

**Files:**
- Modify: `backend/app/security.py`
- Create: `backend/tests/test_password_policy.py`

- [ ] **Étape 1 : Test**

`backend/tests/test_password_policy.py` :

```python
import pytest

from app.security import validate_password_policy


def test_valid_long_password() -> None:
    # Ne lève pas
    validate_password_policy("Un_MotDePasse_Solide_2026!")


def test_too_short() -> None:
    with pytest.raises(ValueError, match="12 caractères"):
        validate_password_policy("trop_court")


def test_common_password_rejected() -> None:
    # "password123" est dans tous les top 100 fuites
    with pytest.raises(ValueError, match="compromis"):
        validate_password_policy("password1234")
```

- [ ] **Étape 2 : Ajouter à `security.py`**

```python
# Ajouter en bas de backend/app/security.py
MIN_PASSWORD_LENGTH = 12

# Top 100 mots de passe les plus compromis (extrait de HIBP / listes publiques)
# Pour le MVP : liste inline. Évolution v2 : fichier hash SHA-1 complet HIBP.
_COMPROMISED = {
    "password1234", "password12345", "123456789012", "qwerty123456",
    "motdepasse12", "azertyuiop12", "admin1234567", "welcome12345",
    # + étendue via un fichier texte en prod
}


def validate_password_policy(raw: str) -> None:
    if len(raw) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Le mot de passe doit contenir au moins {MIN_PASSWORD_LENGTH} caractères"
        )
    if raw.lower() in _COMPROMISED:
        raise ValueError(
            "Ce mot de passe est compromis (présent dans des fuites publiques). "
            "Choisissez-en un autre."
        )
```

- [ ] **Étape 3 : Test + commit**

```bash
cd backend
pytest tests/test_password_policy.py -v
cd ..
git add backend/app/security.py backend/tests/test_password_policy.py
git commit -m "feat(backend): password policy validation"
```

---

### Tâche E3 : Signed session cookies (via itsdangerous)

**Files:**
- Modify: `backend/app/security.py`
- Create: `backend/tests/test_session_cookies.py`

- [ ] **Étape 1 : Test**

`backend/tests/test_session_cookies.py` :

```python
import pytest

from app.security import SessionTokenError, decode_session_token, encode_session_token


def test_encode_decode_roundtrip() -> None:
    secret = "x" * 32
    token = encode_session_token(user_id=42, secret=secret, max_age_seconds=3600)
    assert decode_session_token(token, secret=secret, max_age_seconds=3600) == 42


def test_expired_token_rejected() -> None:
    secret = "x" * 32
    token = encode_session_token(user_id=7, secret=secret, max_age_seconds=-1)
    with pytest.raises(SessionTokenError):
        decode_session_token(token, secret=secret, max_age_seconds=0)


def test_tampered_token_rejected() -> None:
    secret = "x" * 32
    token = encode_session_token(user_id=7, secret=secret, max_age_seconds=3600)
    with pytest.raises(SessionTokenError):
        decode_session_token(token + "tamper", secret=secret, max_age_seconds=3600)
```

- [ ] **Étape 2 : Ajouter à `security.py`**

```python
# En haut du fichier
from itsdangerous import BadSignature, SignatureExpired, TimestampSigner

# En bas du fichier
class SessionTokenError(Exception):
    """Token de session invalide ou expiré."""


def encode_session_token(*, user_id: int, secret: str, max_age_seconds: int) -> str:
    # Le max_age est vérifié au décodage ; encode_session_token ne porte pas d'horodatage
    # explicitement — TimestampSigner le fait pour nous.
    signer = TimestampSigner(secret)
    return signer.sign(str(user_id)).decode("utf-8")


def decode_session_token(token: str, *, secret: str, max_age_seconds: int) -> int:
    signer = TimestampSigner(secret)
    try:
        raw = signer.unsign(token, max_age=max_age_seconds).decode("utf-8")
    except SignatureExpired as exc:
        raise SessionTokenError("Session expirée") from exc
    except BadSignature as exc:
        raise SessionTokenError("Token invalide") from exc
    try:
        return int(raw)
    except ValueError as exc:
        raise SessionTokenError("Format de token invalide") from exc
```

- [ ] **Étape 3 : Test + commit**

```bash
cd backend
pytest tests/test_session_cookies.py -v
cd ..
git add backend/app/security.py backend/tests/test_session_cookies.py
git commit -m "feat(backend): signed session tokens with itsdangerous"
```

---

### Tâche E4 : Dépendance FastAPI `get_current_user`

**Files:**
- Create: `backend/app/deps.py`
- Create: `backend/tests/test_deps.py`

- [ ] **Étape 1 : Test**

`backend/tests/test_deps.py` :

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.deps import get_current_user
from app.models.user import User, UserRole
from app.security import encode_session_token

SECRET = "a" * 32
COOKIE_NAME = "session"


def _make_app(db_session: Session) -> FastAPI:
    app = FastAPI()

    def override_db():
        yield db_session

    from app.db import get_db

    app.dependency_overrides[get_db] = override_db

    @app.get("/protected")
    def protected(current=get_current_user):
        return {"email": current.email}

    return app


def test_requires_cookie(db_session: Session) -> None:
    app = _make_app(db_session)
    client = TestClient(app)
    r = client.get("/protected")
    assert r.status_code == 401
```

(Note : ce test est volontairement rudimentaire. Il sera complété à la tâche F.)

- [ ] **Étape 2 : Implémenter**

`backend/app/deps.py` :

```python
from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models.user import User
from app.security import SessionTokenError, decode_session_token

COOKIE_NAME = "session"


def get_current_user(
    session: str | None = Cookie(default=None, alias=COOKIE_NAME),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> User:
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Non authentifié")
    try:
        user_id = decode_session_token(
            session,
            secret=settings.secret_key,
            max_age_seconds=settings.session_hours * 3600,
        )
    except SessionTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur inconnu ou désactivé"
        )
    return user


def require_admin(current: User = Depends(get_current_user)) -> User:
    from app.models.user import UserRole

    if current.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Droits administrateur requis"
        )
    return current
```

- [ ] **Étape 3 : Test + commit**

```bash
cd backend
pytest tests/test_deps.py -v
cd ..
git add backend/app/deps.py backend/tests/test_deps.py
git commit -m "feat(backend): get_current_user dependency and require_admin"
```

---

### Tâche E5 : Configurer slowapi pour le rate limiting

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Étape 1 : Mettre à jour `main.py`**

```python
# backend/app/main.py
from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Outil de trésorerie",
    description="API de l'outil de gestion de trésorerie auto-hébergé",
    version="0.1.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "name": "tresorerie-backend"}
```

- [ ] **Étape 2 : Test minimal**

Ajouter un test pour vérifier que l'import et l'instanciation du limiter fonctionnent :

```python
# backend/tests/test_limiter_init.py
from app.main import app, limiter


def test_limiter_attached() -> None:
    assert app.state.limiter is limiter
```

- [ ] **Étape 3 : Commit**

```bash
cd backend
pytest tests/test_limiter_init.py -v
cd ..
git add backend/app/main.py backend/tests/test_limiter_init.py
git commit -m "feat(backend): attach slowapi limiter to app"
```

---

# SECTION F — API : Auth + /me + Admin CRUD

### Tâche F1 : Schémas Pydantic (DTOs)

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/schemas/user.py`
- Create: `backend/app/schemas/entity.py`
- Create: `backend/app/schemas/bank_account.py`

- [ ] **Étape 1 : Créer tous les schémas**

`backend/app/schemas/__init__.py` : vide ou `""`.

`backend/app/schemas/auth.py` :

```python
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    id: int
    email: EmailStr
    role: str
    full_name: str | None = None
```

`backend/app/schemas/user.py` :

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: UserRole
    full_name: str | None
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=200)
    role: UserRole = UserRole.READER
    full_name: str | None = None


class UserUpdate(BaseModel):
    role: UserRole | None = None
    full_name: str | None = None
    is_active: bool | None = None
```

`backend/app/schemas/entity.py` :

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EntityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    legal_name: str
    siret: str | None
    parent_entity_id: int | None
    created_at: datetime


class EntityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    legal_name: str = Field(min_length=1, max_length=255)
    siret: str | None = Field(default=None, max_length=32)
    parent_entity_id: int | None = None


class EntityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    legal_name: str | None = Field(default=None, min_length=1, max_length=255)
    siret: str | None = Field(default=None, max_length=32)
    parent_entity_id: int | None = None
```

`backend/app/schemas/bank_account.py` :

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BankAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_id: int
    name: str
    iban: str
    bic: str | None
    bank_name: str
    bank_code: str
    account_number: str | None
    currency: str
    is_active: bool
    created_at: datetime


class BankAccountCreate(BaseModel):
    entity_id: int
    name: str = Field(min_length=1, max_length=255)
    iban: str = Field(min_length=14, max_length=34)
    bic: str | None = Field(default=None, max_length=11)
    bank_name: str = Field(min_length=1, max_length=255)
    bank_code: str = Field(min_length=1, max_length=50)
    account_number: str | None = Field(default=None, max_length=34)
    currency: str = Field(default="EUR", min_length=3, max_length=3)


class BankAccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    bic: str | None = Field(default=None, max_length=11)
    bank_name: str | None = Field(default=None, min_length=1, max_length=255)
    bank_code: str | None = Field(default=None, min_length=1, max_length=50)
    is_active: bool | None = None
```

- [ ] **Étape 2 : Commit**

```bash
cd ..
git add backend/app/schemas
git commit -m "feat(backend): add pydantic DTOs for users, entities, bank accounts, auth"
```

---

### Tâche F2 : Endpoint `/api/auth/login` + `/api/auth/logout` + `/api/me`

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/router.py`
- Create: `backend/app/api/auth.py`
- Create: `backend/app/api/me.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_auth_api.py`

- [ ] **Étape 1 : Tests**

`backend/tests/test_auth_api.py` :

```python
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import get_db
from app.main import app
from app.models.user import User, UserRole
from app.security import hash_password


def _override_db(session: Session):
    def _inner():
        yield session

    return _inner


def test_login_then_me(db_session: Session) -> None:
    user = User(
        email="admin@test.local",
        password_hash=hash_password("MotDePasseSolide2026!"),
        role=UserRole.ADMIN,
        full_name="Admin",
    )
    db_session.add(user)
    db_session.commit()

    app.dependency_overrides[get_db] = _override_db(db_session)
    client = TestClient(app)

    r = client.post(
        "/api/auth/login",
        json={"email": "admin@test.local", "password": "MotDePasseSolide2026!"},
    )
    assert r.status_code == 200
    assert r.json()["email"] == "admin@test.local"

    r2 = client.get("/api/me")
    assert r2.status_code == 200
    assert r2.json()["email"] == "admin@test.local"

    r3 = client.post("/api/auth/logout")
    assert r3.status_code == 204

    r4 = client.get("/api/me")
    assert r4.status_code == 401

    app.dependency_overrides.clear()


def test_wrong_password(db_session: Session) -> None:
    user = User(email="u@x.com", password_hash=hash_password("MotDePasseSolide2026!"))
    db_session.add(user)
    db_session.commit()

    app.dependency_overrides[get_db] = _override_db(db_session)
    client = TestClient(app)

    r = client.post(
        "/api/auth/login",
        json={"email": "u@x.com", "password": "wrong"},
    )
    assert r.status_code == 401
    app.dependency_overrides.clear()
```

- [ ] **Étape 2 : Implémenter `api/auth.py`**

```python
# backend/app/api/auth.py
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.deps import COOKIE_NAME
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse
from app.security import encode_session_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants invalides"
        )
    token = encode_session_token(
        user_id=user.id,
        secret=settings.secret_key,
        max_age_seconds=settings.session_hours * 3600,
    )
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=settings.session_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=False,  # True en prod via config
    )
    user.last_login_at = datetime.now(UTC)
    db.commit()
    return LoginResponse(
        id=user.id, email=user.email, role=user.role.value, full_name=user.full_name
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME)
```

- [ ] **Étape 3 : Implémenter `api/me.py`**

```python
# backend/app/api/me.py
from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserRead

router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("", response_model=UserRead)
def me(current: User = Depends(get_current_user)) -> User:
    return current
```

- [ ] **Étape 4 : Agréger dans `api/router.py`**

```python
# backend/app/api/router.py
from fastapi import APIRouter

from app.api import auth, me

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(me.router)
```

- [ ] **Étape 5 : Brancher dans `main.py`**

Mettre à jour `backend/app/main.py` :

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.router import api_router
from app.config import get_settings

limiter = Limiter(key_func=get_remote_address)

settings = get_settings()
app = FastAPI(
    title="Outil de trésorerie", description="API...", version="0.1.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "name": "tresorerie-backend"}
```

- [ ] **Étape 6 : Appliquer le rate limit sur /login**

Dans `backend/app/api/auth.py`, ajouter le décorateur :

```python
from app.main import limiter  # attention : import tardif, voir note

# Sur la fonction login :
@limiter.limit("10/minute")
def login(request: ..., ...):
    ...
```

**Note pratique** : pour éviter un cycle d'import, déplacer le limiter dans un module à part. Créer `backend/app/rate_limiter.py` :

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
```

Puis dans `auth.py` : `from app.rate_limiter import limiter` ; et dans `main.py` : `from app.rate_limiter import limiter`.

Et ajouter la `Request` dans la signature de `login` (requis par slowapi) :

```python
from fastapi import Request

@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
def login(request: Request, payload: LoginRequest, ...):
    ...
```

- [ ] **Étape 7 : Tests + commit**

```bash
cd backend
pytest tests/test_auth_api.py -v
cd ..
git add backend/app/api backend/app/rate_limiter.py backend/app/main.py backend/tests/test_auth_api.py
git commit -m "feat(backend): login/logout/me endpoints with session cookie and rate limiting"
```

---

### Tâche F3 : CRUD Users (admin)

**Files:**
- Create: `backend/app/api/users.py`
- Create: `backend/tests/test_users_api.py`
- Modify: `backend/app/api/router.py`

- [ ] **Étape 1 : Tests** (se baser sur la structure de `test_auth_api.py`)

`backend/tests/test_users_api.py` : implémenter au minimum ces tests :
- `test_list_users_requires_admin` (un reader reçoit 403)
- `test_create_user_as_admin`
- `test_create_user_rejects_short_password`
- `test_update_user_role`
- `test_deactivate_user`

(Voir le code déjà commenté dans `test_auth_api.py` pour la plomberie d'override de dépendances et de login programmatique.)

- [ ] **Étape 2 : Implémenter `api/users.py`**

```python
# backend/app/api/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_admin
from app.models.user import User
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.security import hash_password, validate_password_policy

router = APIRouter(prefix="/api/users", tags=["users"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db)) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at.desc())))


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    validate_password_policy(payload.password)
    exists = db.scalar(select(User).where(User.email == payload.email))
    if exists:
        raise HTTPException(status_code=409, detail="Cet email est déjà utilisé")
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        full_name=payload.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserRead)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(user_id: int, db: Session = Depends(get_db)) -> None:
    """Désactivation logique uniquement (pas de delete physique — règle de §4.3)."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    user.is_active = False
    db.commit()
```

- [ ] **Étape 3 : Ajouter au router + test + commit**

```python
# backend/app/api/router.py
from app.api import auth, me, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(me.router)
api_router.include_router(users.router)
```

```bash
cd backend
pytest tests/test_users_api.py -v
cd ..
git add backend/app/api/users.py backend/app/api/router.py backend/tests/test_users_api.py
git commit -m "feat(backend): admin CRUD for users"
```

---

### Tâche F4 : CRUD Entities (admin)

**Files:**
- Create: `backend/app/api/entities.py`
- Create: `backend/tests/test_entities_api.py`
- Modify: `backend/app/api/router.py`

- [ ] **Étape 1 : Tests** (mêmes patterns : list/create/update/delete, certains admin-only)

Tests clés :
- `test_create_entity_basic`
- `test_create_entity_with_parent`
- `test_reject_self_parent`
- `test_list_entities_ordered`

- [ ] **Étape 2 : Implémenter `api/entities.py`**

Structure copiée de `api/users.py` mais pour `Entity`, avec vérifications :
- Refuser parent_entity_id == id (règle du modèle)
- Refuser suppression si des comptes bancaires ou des transactions y sont rattachés (pour l'instant uniquement comptes bancaires)

```python
# backend/app/api/entities.py (esquisse)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_admin
from app.models.entity import Entity, validate_entity_tree
from app.models.bank_account import BankAccount
from app.schemas.entity import EntityCreate, EntityRead, EntityUpdate

router = APIRouter(
    prefix="/api/entities", tags=["entities"], dependencies=[Depends(require_admin)]
)


@router.get("", response_model=list[EntityRead])
def list_entities(db: Session = Depends(get_db)) -> list[Entity]:
    return list(db.scalars(select(Entity).order_by(Entity.name)))


@router.post("", response_model=EntityRead, status_code=status.HTTP_201_CREATED)
def create_entity(payload: EntityCreate, db: Session = Depends(get_db)) -> Entity:
    e = Entity(**payload.model_dump())
    # validate_entity_tree vérifie self-ref mais Entity n'a pas encore d'id à la création
    db.add(e)
    db.flush()
    validate_entity_tree(e)
    db.commit()
    db.refresh(e)
    return e


@router.patch("/{entity_id}", response_model=EntityRead)
def update_entity(
    entity_id: int, payload: EntityUpdate, db: Session = Depends(get_db)
) -> Entity:
    e = db.get(Entity, entity_id)
    if e is None:
        raise HTTPException(status_code=404, detail="Société introuvable")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(e, field, value)
    validate_entity_tree(e)
    db.commit()
    db.refresh(e)
    return e


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entity(entity_id: int, db: Session = Depends(get_db)) -> None:
    e = db.get(Entity, entity_id)
    if e is None:
        raise HTTPException(status_code=404, detail="Société introuvable")
    has_accounts = db.scalar(
        select(BankAccount.id).where(BankAccount.entity_id == entity_id)
    )
    if has_accounts:
        raise HTTPException(
            status_code=409,
            detail="Impossible de supprimer : des comptes bancaires sont rattachés",
        )
    has_children = db.scalar(select(Entity.id).where(Entity.parent_entity_id == entity_id))
    if has_children:
        raise HTTPException(
            status_code=409,
            detail="Impossible de supprimer : des filiales sont rattachées",
        )
    db.delete(e)
    db.commit()
```

- [ ] **Étape 3 : Router + tests + commit**

```bash
cd backend
pytest tests/test_entities_api.py -v
cd ..
git add backend/app/api/entities.py backend/app/api/router.py backend/tests/test_entities_api.py
git commit -m "feat(backend): admin CRUD for entities"
```

---

### Tâche F5 : CRUD BankAccounts (admin)

**Files:**
- Create: `backend/app/api/bank_accounts.py`
- Create: `backend/tests/test_bank_accounts_api.py`
- Modify: `backend/app/api/router.py`

Mêmes patterns. Points d'attention :
- `iban` est unique : gestion propre du 409 Conflict
- `entity_id` doit exister : 404 sinon

Structure à recopier de `entities.py` avec les adaptations. (Tâche tracée en 5 étapes TDD standard.)

---

### Tâche F6 : Endpoint d'amorçage `/api/bootstrap` (premier admin)

**Files:**
- Create: `backend/app/api/bootstrap.py`
- Create: `backend/tests/test_bootstrap.py`

Ce endpoint est unique : il permet **uniquement quand il n'y a encore aucun utilisateur** de créer le premier compte admin sans authentification. Une fois un admin existant, il renvoie 409.

- [ ] **Étape 1 : Test**

`backend/tests/test_bootstrap.py` :

```python
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import get_db
from app.main import app


def _override_db(session: Session):
    def _inner():
        yield session

    return _inner


def test_bootstrap_creates_first_admin(db_session: Session) -> None:
    app.dependency_overrides[get_db] = _override_db(db_session)
    client = TestClient(app)
    r = client.post(
        "/api/bootstrap",
        json={
            "email": "admin@test.local",
            "password": "MotDePasseSolide2026!",
            "full_name": "Admin",
        },
    )
    assert r.status_code == 201
    app.dependency_overrides.clear()


def test_bootstrap_refused_if_user_exists(db_session: Session) -> None:
    from app.models.user import User, UserRole
    from app.security import hash_password

    db_session.add(User(email="x@y.com", password_hash=hash_password("x"*12), role=UserRole.ADMIN))
    db_session.commit()

    app.dependency_overrides[get_db] = _override_db(db_session)
    client = TestClient(app)
    r = client.post(
        "/api/bootstrap",
        json={"email": "a@b.com", "password": "MotDePasseSolide2026!"},
    )
    assert r.status_code == 409
    app.dependency_overrides.clear()
```

- [ ] **Étape 2 : Implémenter**

```python
# backend/app/api/bootstrap.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserRead
from app.security import hash_password, validate_password_policy

router = APIRouter(prefix="/api/bootstrap", tags=["bootstrap"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def bootstrap_first_admin(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    already = db.scalar(select(User).limit(1))
    if already is not None:
        raise HTTPException(
            status_code=409, detail="L'amorçage est déjà effectué"
        )
    validate_password_policy(payload.password)
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole.ADMIN,
        full_name=payload.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
```

- [ ] **Étape 3 : Router + tests + commit**

```bash
cd backend
pytest tests/test_bootstrap.py -v
cd ..
git add backend/app/api/bootstrap.py backend/app/api/router.py backend/tests/test_bootstrap.py
git commit -m "feat(backend): one-shot bootstrap endpoint for first admin"
```

---

# SECTION G — Santé et observabilité de base

### Tâche G1 : Endpoints `/healthz` et `/readyz`

**Files:**
- Create: `backend/app/api/health.py`
- Create: `backend/tests/test_health_endpoints.py`
- Modify: `backend/app/api/router.py`

- [ ] **Étape 1 : Tests**

`backend/tests/test_health_endpoints.py` :

```python
from fastapi.testclient import TestClient

from app.main import app


def test_healthz() -> None:
    client = TestClient(app)
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "alive"}


def test_readyz_when_db_up() -> None:
    client = TestClient(app)
    r = client.get("/readyz")
    # L'état dépend de la DB. En test on a la DB de test disponible via conftest.
    assert r.status_code in (200, 503)
```

- [ ] **Étape 2 : Implémenter**

```python
# backend/app/api/health.py
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/readyz")
def readyz(db: Session = Depends(get_db)) -> JSONResponse:
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"status": "db_unavailable"})
    return JSONResponse(status_code=200, content={"status": "ready"})
```

- [ ] **Étape 3 : Brancher + commit**

```python
# router.py : include_router(health.router)
```

```bash
cd backend
pytest tests/test_health_endpoints.py -v
cd ..
git add backend/app/api/health.py backend/app/api/router.py backend/tests/test_health_endpoints.py
git commit -m "feat(backend): healthz and readyz endpoints"
```

---

### Tâche G2 : Logger structuré JSON

**Files:**
- Create: `backend/app/logging_config.py`
- Modify: `backend/app/main.py`

- [ ] **Étape 1 : Ajouter la configuration**

```python
# backend/app/logging_config.py
import json
import logging
import sys
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
```

- [ ] **Étape 2 : Appeler dans `main.py`**

```python
# En haut de main.py :
from app.logging_config import configure_logging

configure_logging()
```

- [ ] **Étape 3 : Commit**

```bash
git add backend/app/logging_config.py backend/app/main.py
git commit -m "feat(backend): structured JSON logging"
```

---

# SECTION H — Frontend : squelette Vite + React + Tailwind + shadcn

### Tâche H1 : Initialiser le projet Vite

**Files:**
- Create: tous les fichiers de base Vite/React/TS dans `frontend/`

- [ ] **Étape 1 : Initialiser**

```bash
cd "C:/Users/trist/Documents/Outil/Clone AGICAP/frontend"
# Supprimer le .gitkeep éventuel
rm -f .gitkeep
# Vite template
npm create vite@latest . -- --template react-ts
# Répondre aux prompts (ignorer si déjà créé)
npm install
npm run dev
```
Vérifier sur `http://localhost:5173` que la page Vite par défaut s'affiche. Puis Ctrl+C.

- [ ] **Étape 2 : Nettoyer les fichiers Vite initiaux**

Supprimer `src/App.css`, le contenu par défaut de `src/App.tsx`, `src/index.css` (à remplacer).

- [ ] **Étape 3 : Commit**

```bash
cd ..
git add frontend/
git commit -m "chore(frontend): scaffold vite + react + typescript"
```

---

### Tâche H2 : Installer Tailwind + shadcn/ui

- [ ] **Étape 1 : Tailwind**

```bash
cd frontend
npm install -D tailwindcss@3 postcss autoprefixer
npx tailwindcss init -p
```

Modifier `frontend/tailwind.config.ts` :

```ts
import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {},
  },
  plugins: [],
} satisfies Config;
```

Remplacer `frontend/src/index.css` :

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  font-family: ui-sans-serif, system-ui, sans-serif;
  @apply bg-slate-50 text-slate-900;
}
```

- [ ] **Étape 2 : Configurer shadcn/ui**

```bash
npx shadcn@latest init
# Choisir : TypeScript, style "default", couleur "slate", CSS variables
```

Puis installer quelques composants de base :

```bash
npx shadcn@latest add button input label card form table toast dialog select
```

- [ ] **Étape 3 : Vérifier**

Modifier `frontend/src/App.tsx` temporairement pour afficher un bouton shadcn :

```tsx
import { Button } from '@/components/ui/button';

export default function App() {
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold">Outil de trésorerie</h1>
      <Button className="mt-4">Bouton de test</Button>
    </div>
  );
}
```

Lancer `npm run dev`, vérifier visuellement le bouton stylé.

- [ ] **Étape 4 : Commit**

```bash
cd ..
git add frontend/
git commit -m "feat(frontend): tailwind and shadcn/ui setup"
```

---

### Tâche H3 : Router et client API

**Files:**
- Create: `frontend/src/router.tsx`
- Create: `frontend/src/api/client.ts`

- [ ] **Étape 1 : Installer React Router**

```bash
cd frontend
npm install react-router-dom
```

- [ ] **Étape 2 : Créer `src/api/client.ts`**

```ts
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export class ApiError extends Error {
  constructor(public status: number, public detail: string) {
    super(detail);
  }
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers ?? {}),
    },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}
```

- [ ] **Étape 3 : Router et structure des pages**

`frontend/src/router.tsx` :

```tsx
import { createBrowserRouter, Navigate } from 'react-router-dom';

import { Layout } from '@/components/Layout';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { AdminBankAccountsPage } from '@/pages/AdminBankAccountsPage';
import { AdminEntitiesPage } from '@/pages/AdminEntitiesPage';
import { AdminUsersPage } from '@/pages/AdminUsersPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { LoginPage } from '@/pages/LoginPage';

export const router = createBrowserRouter([
  { path: '/connexion', element: <LoginPage /> },
  {
    element: (
      <ProtectedRoute>
        <Layout />
      </ProtectedRoute>
    ),
    children: [
      { path: '/', element: <Navigate to="/tableau-de-bord" replace /> },
      { path: '/tableau-de-bord', element: <DashboardPage /> },
      { path: '/administration/utilisateurs', element: <AdminUsersPage /> },
      { path: '/administration/societes', element: <AdminEntitiesPage /> },
      { path: '/administration/comptes-bancaires', element: <AdminBankAccountsPage /> },
    ],
  },
]);
```

(Les pages listées seront créées aux tâches suivantes, mais elles peuvent commencer en placeholders très courts.)

- [ ] **Étape 4 : Créer `src/main.tsx`**

```tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import './index.css';
import { router } from './router';

const queryClient = new QueryClient();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>
);
```

```bash
npm install @tanstack/react-query
```

- [ ] **Étape 5 : Commit**

```bash
cd ..
git add frontend/
git commit -m "feat(frontend): router, tanstack query and api client"
```

---

### Tâche H4 : Vitest + Testing Library

- [ ] **Étape 1 : Installer**

```bash
cd frontend
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```

- [ ] **Étape 2 : Configurer**

Modifier `frontend/vite.config.ts` :

```ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
  },
});
```

Créer `frontend/src/test/setup.ts` :

```ts
import '@testing-library/jest-dom/vitest';
```

Ajouter à `package.json` :

```json
"scripts": {
  "dev": "vite",
  "build": "tsc -b && vite build",
  "lint": "eslint .",
  "preview": "vite preview",
  "test": "vitest --run",
  "test:watch": "vitest"
}
```

- [ ] **Étape 3 : Test de fumée**

Créer `frontend/src/test/smoke.test.ts` :

```ts
import { describe, expect, it } from 'vitest';

describe('smoke', () => {
  it('basic math', () => {
    expect(1 + 1).toBe(2);
  });
});
```

Lancer : `npm test`. Doit passer.

- [ ] **Étape 4 : Commit**

```bash
cd ..
git add frontend/
git commit -m "chore(frontend): vitest + testing library setup"
```

---

### Tâche H5 : Hook `useAuth` et wrapper API auth

**Files:**
- Create: `frontend/src/api/auth.ts`
- Create: `frontend/src/hooks/useAuth.ts`
- Create: `frontend/src/types/api.ts`

- [ ] **Étape 1 : Types API**

`frontend/src/types/api.ts` :

```ts
export type UserRole = 'admin' | 'reader';

export type Me = {
  id: number;
  email: string;
  role: UserRole;
  fullName: string | null;
  isActive: boolean;
  createdAt: string;
  lastLoginAt: string | null;
};

export type Entity = {
  id: number;
  name: string;
  legalName: string;
  siret: string | null;
  parentEntityId: number | null;
  createdAt: string;
};

export type BankAccount = {
  id: number;
  entityId: number;
  name: string;
  iban: string;
  bic: string | null;
  bankName: string;
  bankCode: string;
  currency: string;
  isActive: boolean;
  createdAt: string;
};
```

(Note : les champs viennent de l'API en `snake_case` mais on les convertit en `camelCase` dans le client. Soit manuellement, soit avec une transformation centralisée. Pour garder ça simple, faire la transformation dans chaque fonction `api/*` en attendant de mettre un helper centralisé.)

- [ ] **Étape 2 : `api/auth.ts`**

```ts
import { apiFetch } from './client';

export type LoginInput = { email: string; password: string };

export async function login(input: LoginInput): Promise<void> {
  await apiFetch<unknown>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function logout(): Promise<void> {
  await apiFetch<unknown>('/api/auth/logout', { method: 'POST' });
}
```

- [ ] **Étape 3 : `api/me.ts`**

```ts
// frontend/src/api/me.ts
import { apiFetch } from './client';
import type { Me } from '@/types/api';

type RawMe = {
  id: number;
  email: string;
  role: 'admin' | 'reader';
  full_name: string | null;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
};

export async function getMe(): Promise<Me> {
  const raw = await apiFetch<RawMe>('/api/me');
  return {
    id: raw.id,
    email: raw.email,
    role: raw.role,
    fullName: raw.full_name,
    isActive: raw.is_active,
    createdAt: raw.created_at,
    lastLoginAt: raw.last_login_at,
  };
}
```

- [ ] **Étape 4 : `hooks/useAuth.ts`**

```ts
// frontend/src/hooks/useAuth.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';

import { login as apiLogin, logout as apiLogout } from '@/api/auth';
import { getMe } from '@/api/me';
import { ApiError } from '@/api/client';

export function useMe() {
  return useQuery({
    queryKey: ['me'],
    queryFn: getMe,
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status === 401) return false;
      return failureCount < 2;
    },
  });
}

export function useLogin() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  return useMutation({
    mutationFn: apiLogin,
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['me'] });
      navigate('/tableau-de-bord');
    },
  });
}

export function useLogout() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  return useMutation({
    mutationFn: apiLogout,
    onSuccess: () => {
      qc.clear();
      navigate('/connexion');
    },
  });
}
```

- [ ] **Étape 5 : Commit**

```bash
cd ..
git add frontend/src
git commit -m "feat(frontend): auth API client and useAuth hooks"
```

---

# SECTION I — Frontend : authentification, layout, pages admin

### Tâche I1 : Page `LoginPage`

**Files:**
- Create: `frontend/src/pages/LoginPage.tsx`
- Create: `frontend/src/test/LoginPage.test.tsx`

- [ ] **Étape 1 : Test**

`frontend/src/test/LoginPage.test.tsx` (test minimal : la page s'affiche avec email/mot de passe) :

```tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import { LoginPage } from '@/pages/LoginPage';

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

test('affiche les champs email et mot de passe', () => {
  wrap(<LoginPage />);
  expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/mot de passe/i)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /se connecter/i })).toBeInTheDocument();
});
```

- [ ] **Étape 2 : Implémenter**

```tsx
// frontend/src/pages/LoginPage.tsx
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useLogin } from '@/hooks/useAuth';
import { ApiError } from '@/api/client';

export function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const login = useLogin();

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <form
        className="bg-white p-8 rounded-lg shadow w-96 space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          login.mutate({ email, password });
        }}
      >
        <h1 className="text-2xl font-bold">Connexion</h1>

        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="password">Mot de passe</Label>
          <Input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>

        {login.error instanceof ApiError && (
          <p className="text-red-600 text-sm">{login.error.detail}</p>
        )}

        <Button type="submit" className="w-full" disabled={login.isPending}>
          {login.isPending ? 'Connexion…' : 'Se connecter'}
        </Button>
      </form>
    </div>
  );
}
```

- [ ] **Étape 3 : Test + commit**

```bash
cd frontend
npm test -- LoginPage.test.tsx
cd ..
git add frontend/src/pages/LoginPage.tsx frontend/src/test/LoginPage.test.tsx
git commit -m "feat(frontend): login page"
```

---

### Tâche I2 : `ProtectedRoute` et Layout

**Files:**
- Create: `frontend/src/components/ProtectedRoute.tsx`
- Create: `frontend/src/components/Layout.tsx`
- Create: `frontend/src/components/Sidebar.tsx`

- [ ] **Étape 1 : Protected route**

```tsx
// frontend/src/components/ProtectedRoute.tsx
import { Navigate } from 'react-router-dom';

import { useMe } from '@/hooks/useAuth';

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const me = useMe();
  if (me.isLoading) return <div className="p-8">Chargement…</div>;
  if (me.isError || !me.data) return <Navigate to="/connexion" replace />;
  return <>{children}</>;
}
```

- [ ] **Étape 2 : Sidebar**

```tsx
// frontend/src/components/Sidebar.tsx
import { NavLink } from 'react-router-dom';

import { Button } from '@/components/ui/button';
import { useLogout, useMe } from '@/hooks/useAuth';

const items = [
  { to: '/tableau-de-bord', label: 'Tableau de bord' },
  { to: '/administration/utilisateurs', label: 'Utilisateurs', adminOnly: true },
  { to: '/administration/societes', label: 'Sociétés', adminOnly: true },
  { to: '/administration/comptes-bancaires', label: 'Comptes bancaires', adminOnly: true },
];

export function Sidebar() {
  const me = useMe();
  const logout = useLogout();
  const isAdmin = me.data?.role === 'admin';

  return (
    <aside className="w-64 min-h-screen bg-white border-r border-slate-200 p-4 flex flex-col">
      <h2 className="text-xl font-bold mb-6">Trésorerie</h2>
      <nav className="flex-1 space-y-1">
        {items
          .filter((i) => !i.adminOnly || isAdmin)
          .map((i) => (
            <NavLink
              key={i.to}
              to={i.to}
              className={({ isActive }) =>
                `block px-3 py-2 rounded hover:bg-slate-100 ${
                  isActive ? 'bg-slate-100 font-medium' : ''
                }`
              }
            >
              {i.label}
            </NavLink>
          ))}
      </nav>
      <div className="pt-4 border-t border-slate-200 text-sm text-slate-600">
        <p>{me.data?.fullName ?? me.data?.email}</p>
        <Button
          variant="outline"
          className="mt-2 w-full"
          onClick={() => logout.mutate()}
        >
          Déconnexion
        </Button>
      </div>
    </aside>
  );
}
```

- [ ] **Étape 3 : Layout**

```tsx
// frontend/src/components/Layout.tsx
import { Outlet } from 'react-router-dom';

import { Sidebar } from '@/components/Sidebar';

export function Layout() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <Outlet />
      </main>
    </div>
  );
}
```

- [ ] **Étape 4 : Commit**

```bash
git add frontend/src/components
git commit -m "feat(frontend): protected route, sidebar and layout"
```

---

### Tâche I3 : Page `DashboardPage` (placeholder)

**Files:**
- Create: `frontend/src/pages/DashboardPage.tsx`

- [ ] **Étape 1 : Créer**

```tsx
// frontend/src/pages/DashboardPage.tsx
export function DashboardPage() {
  return (
    <div>
      <h1 className="text-3xl font-bold">Tableau de bord</h1>
      <p className="mt-2 text-slate-600">
        Les indicateurs et graphiques seront ajoutés dans le Plan 3.
      </p>
    </div>
  );
}
```

- [ ] **Étape 2 : Commit**

```bash
git add frontend/src/pages/DashboardPage.tsx
git commit -m "feat(frontend): dashboard placeholder page"
```

---

### Tâche I4 : Page `AdminUsersPage` (liste + création)

**Files:**
- Create: `frontend/src/pages/AdminUsersPage.tsx`
- Create: `frontend/src/api/users.ts`

- [ ] **Étape 1 : Client API users**

```ts
// frontend/src/api/users.ts
import { apiFetch } from './client';
import type { Me, UserRole } from '@/types/api';

type RawUser = {
  id: number;
  email: string;
  role: UserRole;
  full_name: string | null;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
};

export type User = Me; // même shape

function mapUser(r: RawUser): User {
  return {
    id: r.id,
    email: r.email,
    role: r.role,
    fullName: r.full_name,
    isActive: r.is_active,
    createdAt: r.created_at,
    lastLoginAt: r.last_login_at,
  };
}

export async function listUsers(): Promise<User[]> {
  const raw = await apiFetch<RawUser[]>('/api/users');
  return raw.map(mapUser);
}

export type CreateUserInput = {
  email: string;
  password: string;
  role: UserRole;
  fullName?: string;
};

export async function createUser(input: CreateUserInput): Promise<User> {
  const r = await apiFetch<RawUser>('/api/users', {
    method: 'POST',
    body: JSON.stringify({
      email: input.email,
      password: input.password,
      role: input.role,
      full_name: input.fullName,
    }),
  });
  return mapUser(r);
}
```

- [ ] **Étape 2 : Page** (implémenter avec un formulaire shadcn + table — code omis ici pour la taille, inspiré du même pattern que AdminEntitiesPage plus bas)

- [ ] **Étape 3 : Commit**

```bash
git add frontend/src/api/users.ts frontend/src/pages/AdminUsersPage.tsx
git commit -m "feat(frontend): admin users page with creation form"
```

---

### Tâche I5 : Page `AdminEntitiesPage` (liste + création + arborescence)

Structure :
- Liste plate avec indentation visuelle pour montrer la hiérarchie
- Formulaire de création avec sélecteur de parent

Implémentation similaire à AdminUsersPage. Commit après tests manuels.

---

### Tâche I6 : Page `AdminBankAccountsPage`

Structure similaire : liste + création avec validation IBAN visuelle.

---

# SECTION J — Orchestration Docker et test end-to-end

### Tâche J1 : Dockerfile backend

**Files:**
- Create: `backend/Dockerfile`

- [ ] **Étape 1 : Créer**

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

RUN pip install --no-cache-dir -e .

ENV PYTHONUNBUFFERED=1

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

- [ ] **Étape 2 : Commit**

```bash
git add backend/Dockerfile
git commit -m "chore(backend): add Dockerfile"
```

---

### Tâche J2 : Dockerfile frontend + nginx config

**Files:**
- Create: `frontend/Dockerfile`
- Create: `frontend/nginx.conf`

- [ ] **Étape 1 : Dockerfile multi-stage**

```dockerfile
# frontend/Dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# L'URL de l'API est injectée à la build via VITE_API_BASE_URL
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

FROM nginx:alpine AS runtime
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

- [ ] **Étape 2 : `nginx.conf`**

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache des assets
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

- [ ] **Étape 3 : Commit**

```bash
git add frontend/Dockerfile frontend/nginx.conf
git commit -m "chore(frontend): add Dockerfile and nginx config"
```

---

### Tâche J3 : `docker-compose.yml` complet + `Caddyfile`

**Files:**
- Create: `docker-compose.yml`
- Create: `Caddyfile`

- [ ] **Étape 1 : `docker-compose.yml`**

```yaml
# docker-compose.yml (production-like)
version: "3.9"

services:
  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    environment:
      APP_DOMAIN: ${APP_DOMAIN}
      CADDY_EMAIL: ${CADDY_EMAIL}
    depends_on: [backend, frontend]

  frontend:
    build:
      context: ./frontend
      args:
        VITE_API_BASE_URL: https://${APP_DOMAIN}
    restart: unless-stopped
    expose: ["80"]

  backend:
    build: ./backend
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      BACKEND_SECRET_KEY: ${BACKEND_SECRET_KEY}
      BACKEND_SESSION_HOURS: ${BACKEND_SESSION_HOURS:-8}
      BACKEND_CORS_ORIGINS: https://${APP_DOMAIN}
    expose: ["8000"]
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  pg_data:
  caddy_data:
  caddy_config:
```

- [ ] **Étape 2 : `Caddyfile`**

```Caddyfile
{
    email {env.CADDY_EMAIL}
}

{env.APP_DOMAIN} {
    encode gzip

    # API
    handle /api/* {
        reverse_proxy backend:8000
    }
    handle /healthz {
        reverse_proxy backend:8000
    }
    handle /readyz {
        reverse_proxy backend:8000
    }
    handle /docs* {
        reverse_proxy backend:8000
    }
    handle /openapi.json {
        reverse_proxy backend:8000
    }

    # Frontend (tout le reste)
    handle {
        reverse_proxy frontend:80
    }

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
    }
}
```

- [ ] **Étape 3 : Test de build local**

```bash
docker compose build
```
Doit compiler sans erreur.

- [ ] **Étape 4 : Commit**

```bash
git add docker-compose.yml Caddyfile
git commit -m "chore: docker-compose orchestration and Caddy config"
```

---

### Tâche J4 : Test end-to-end : bootstrap + login + création entité + création compte

- [ ] **Étape 1 : Lancer l'ensemble**

```bash
cp .env.example .env
# Éditer .env : remplir APP_DOMAIN=localhost, BACKEND_SECRET_KEY, etc.
docker compose up -d --build
docker compose ps
```
Tous les services doivent être healthy.

- [ ] **Étape 2 : Smoke tests manuels**

Vérifier :
1. `curl http://localhost/healthz` → `{"status":"alive"}`
2. `curl http://localhost/readyz` → 200
3. Ouvrir `http://localhost` dans le navigateur → redirige vers `/connexion`
4. Via l'API ou une page dédiée d'amorçage : appeler `POST /api/bootstrap` pour créer le premier admin
5. Se connecter sur l'interface
6. Créer une société (Holding)
7. Créer une filiale avec la holding comme parent
8. Créer un compte bancaire pour la filiale (Delubac)
9. Se déconnecter, se reconnecter : tout doit toujours être là

- [ ] **Étape 3 : Nettoyer les `.gitkeep`**

```bash
find backend frontend docs -name .gitkeep -delete
git add -u
git commit -m "chore: remove gitkeep files (directories now non-empty)"
```

- [ ] **Étape 4 : Commit final de Plan 0**

```bash
git commit --allow-empty -m "chore: plan 0 — foundation complete"
git tag plan-0-done
```

---

## Checklist d'acceptation du Plan 0

Le Plan 0 est **complet** quand **tous** ces critères sont vérifiés :

- [ ] `docker compose up -d --build` réussit et les 4 services sont healthy
- [ ] `curl http://localhost/healthz` retourne 200 et `{"status":"alive"}`
- [ ] `curl http://localhost/readyz` retourne 200 (et 503 si on coupe la DB)
- [ ] La page de connexion s'affiche à `http://localhost/connexion`
- [ ] L'endpoint `POST /api/bootstrap` permet de créer le premier admin (uniquement quand la base est vide)
- [ ] L'admin peut se connecter et sa session persiste 8 heures
- [ ] L'admin peut créer/lister/modifier/désactiver des utilisateurs via l'UI
- [ ] L'admin peut créer/lister/modifier/supprimer des sociétés (avec hiérarchie holding/filiale)
- [ ] L'admin peut créer/lister/modifier des comptes bancaires rattachés à une société
- [ ] Un utilisateur avec le rôle `reader` ne peut pas accéder aux pages d'administration (403)
- [ ] `pytest` (backend) passe à 100 % avec couverture ≥ 60 % (le seuil 70 % est visé pour la fin du projet, pas encore atteignable avec le seul socle)
- [ ] `npm test` (frontend) passe à 100 %
- [ ] `ruff check`, `ruff format --check`, `mypy app` passent sans erreur
- [ ] Tag `plan-0-done` posé sur le dernier commit

---

## Ce qui n'est PAS dans le Plan 0 (pour mémoire)

- Modèles `transactions`, `categories`, `category_rules`, `counterparties`, `tags`, `imports`, `recurring_templates`, `scheduled_transactions`, `scenarios`, `alerts` → Plans 1 à 5
- Analyseur Delubac et pipeline d'import PDF → Plan 1
- Règles de catégorisation, inbox, apprentissage → Plan 2
- Tableau de bord avec graphiques et KPIs → Plan 3
- Module prévisionnel → Plan 4
- Alertes + SMTP + emails → Plan 5
- Sauvegardes automatiques chiffrées, observabilité Prometheus, tests E2E Playwright → Plan 6
- Déploiement sur Azure (réel) → Plan 6

---

_Fin du Plan 0._
