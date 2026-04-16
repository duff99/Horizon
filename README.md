# Clone Agicap — Outil de gestion de trésorerie

Outil de suivi et prévisionnel de trésorerie auto-hébergé, inspiré d'Agicap.
Import manuel de relevés bancaires PDF, multi-entités (holding + filiales),
multi-utilisateurs.

## Documentation

- **Spécification** : [docs/superpowers/specs/2026-04-16-clone-agicap-design.md](docs/superpowers/specs/2026-04-16-clone-agicap-design.md)
- **Plan 0 — Fondation** : [docs/superpowers/plans/2026-04-16-plan-0-fondation.md](docs/superpowers/plans/2026-04-16-plan-0-fondation.md)
- **Suivi d'avancement** : [docs/superpowers/plans/PROGRESS.md](docs/superpowers/plans/PROGRESS.md)
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
