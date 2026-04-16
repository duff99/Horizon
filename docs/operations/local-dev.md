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
