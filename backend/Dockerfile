FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

RUN pip install --no-cache-dir -e .

ENV PYTHONUNBUFFERED=1

# NOTE (déploiement multi-replica) : `alembic upgrade head` exécuté au démarrage
# fait une course si on scale à N replicas. Pour le MVP (1 seul replica) : OK.
# Si un jour on passe à plusieurs, extraire les migrations dans un job init-container
# séparé (voir Plan 6).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
