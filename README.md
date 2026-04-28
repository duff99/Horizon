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

## Discipline éditoriale

Le fichier `frontend/src/content/documentation.ts` est la **source unique** pour le contenu d'aide affiché à deux endroits :

- la page `/documentation` (guide complet)
- le panneau d'aide latéral (bouton « Aide » en haut à droite, sur chaque page)

**Toute PR qui modifie le comportement d'une page doit mettre à jour la section correspondante de `documentation.ts`** — sinon l'aide affichera une description périmée. Pour raccourcir le contenu dans le panneau sans toucher la doc complète, utiliser le champ optionnel `panel` (cf `DocSectionData`).

## Licence

Propriétaire — utilisation interne uniquement.
