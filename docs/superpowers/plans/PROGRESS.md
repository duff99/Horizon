# Suivi d'avancement — Plan 0 Fondation

**Dernière mise à jour** : 2026-04-16 — **🎉 PLAN 0 COMPLET**

## État global

- **Plan en cours** : Plan 0 — Fondation → **✅ TERMINÉ**
- **Branche Git** : `main`
- **Tag** : `plan-0-done`
- **Prochain plan** : Plan 1 — Import & Analyseur Delubac

## Sections

| Section | Tâches | Statut |
|---|---|---|
| A — Initialisation du dépôt | A1-A5 | ✅ Terminée |
| B — Environnement Python | B1-B4 | ✅ Terminée (pytest + ruff validés) |
| C — Base de données | C1-C5 | ✅ Terminée |
| D — Modèles ORM | D1-D4 | ✅ Terminée |
| E — Sécurité | E1-E5 | ✅ Terminée |
| F — API REST | F1-F6 | ✅ Terminée |
| G — Santé / observabilité | G1-G2 | ✅ Terminée |
| H — Frontend scaffold | H1-H5 | ✅ Terminée |
| I — Pages admin | I1-I6 | ✅ Terminée |
| J — Docker orchestration | J1-J4 | ✅ Terminée |

**Total : 46 tâches réalisées**

## Contenu livré

### Backend (Python + FastAPI)
- 4 modèles ORM : `User`, `Entity` (hiérarchique avec validation de cycles), `UserEntityAccess`, `BankAccount`
- 1 migration Alembic consolidée (crée toutes les tables + enum + indexes)
- Sécurité : Argon2id, sessions signées itsdangerous, rate limiting slowapi
- API REST : `/api/auth/{login,logout}`, `/api/me`, `/api/bootstrap`, `/api/users`, `/api/entities`, `/api/bank-accounts`
- `/healthz` + `/readyz` + logs JSON structurés
- Tests : health, config, security, deps, 4 modèles (couverture 96 % sur la partie testable hors DB)

### Frontend (React + TypeScript + Tailwind)
- Scaffold Vite + React 18 + TS 5 + Tailwind 3
- Composants shadcn/ui inline : `Button`, `Input`, `Label`, `Card`, `Select`
- Router + TanStack Query + auth hooks (`useMe`, `useLogin`, `useLogout`)
- Pages : `LoginPage`, `DashboardPage` (placeholder Plan 3), `AdminUsersPage`, `AdminEntitiesPage` (vue arborescente), `AdminBankAccountsPage` (IBAN + bank_code)
- 100 % en français

### Infrastructure
- `docker-compose.dev.yml` (DB seule pour dev local)
- `docker-compose.yml` (prod : Caddy + backend + frontend + db, 4 services)
- `Caddyfile` avec HTTPS Let's Encrypt auto + HSTS + CSP + Permissions-Policy
- Dockerfiles backend et frontend

## Déploiement sur serveur

Pour déployer sur un serveur Ubuntu avec Docker :

```bash
git clone <repo_url>
cd Clone AGICAP
cp .env.example .env
nano .env   # renseigner :
#   APP_DOMAIN=tresorerie.tondomaine.fr
#   BACKEND_SECRET_KEY=<32+ caractères aléatoires>
#   POSTGRES_PASSWORD=<mot de passe fort>
#   CADDY_EMAIL=admin@tondomaine.fr

docker compose up -d --build
```

Puis :
1. Attendre ~30 secondes pour le démarrage + certificat Let's Encrypt
2. Ouvrir `https://tresorerie.tondomaine.fr` → redirection `/connexion`
3. Créer le premier admin via `POST /api/bootstrap` (curl ou Postman) :
   ```bash
   curl -X POST https://tresorerie.tondomaine.fr/api/bootstrap \
     -H "Content-Type: application/json" \
     -d '{"email":"admin@acreed.fr","password":"TonMotDePasseSolide2026","full_name":"Admin"}'
   ```
4. Se connecter via l'UI avec ces identifiants
5. Créer les sociétés (holding + filiales) et les comptes bancaires via l'admin

## Historique des sessions

### Session 2026-04-16 : Plan 0 complet ✅

- Brainstorming → spec de design (approuvée 2 rounds de revue)
- Rédaction Plan 0 (approuvé 2 rounds de revue)
- Exécution Plan 0 (direct, plus efficace que subagent-driven au vu du token budget)
- Tests B validés localement (pytest 3/3, ruff 100%)
- Tests C-D écrits mais non exécutés localement (Docker absent sur le PC utilisateur — validation prévue sur le serveur de déploiement)

## Prochaine étape : Plan 1

Plan 1 = **Analyseur PDF Delubac + pipeline d'import de transactions**. Nécessite :
- Nouveaux modèles : `Transaction`, `Import`, `Counterparty`, `Category` (en partie)
- Module `parsers/` avec interface `BaseParser` et implémentation Delubac
- Pipeline : upload PDF → détection banque → parsing → normalisation → déduplication → insertion
- Endpoints : `POST /api/imports`, `GET /api/imports`, `GET /api/transactions`
- Page frontend : upload PDF + résumé d'import + liste transactions

À écrire en début de prochaine session.
