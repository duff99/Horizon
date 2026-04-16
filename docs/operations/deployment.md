# Déploiement production

Cible : `horizon.acreedconsulting.com` sur le serveur ACREED CONSULTING.

## Contexte infra

Le serveur héberge une quinzaine d'applications derrière un **nginx natif**
qui gère aussi le TLS via **certbot**. Les ports 80/443 sont déjà occupés, donc
le service `caddy` du compose par défaut n'est pas utilisable en production.

Le fichier `docker-compose.prod.yml` publie frontend et backend uniquement sur
la loopback (`127.0.0.1:8100` et `127.0.0.1:8101`) ; le vhost nginx reverse-proxy.

## Procédure

### 1. Secrets

```bash
cp .env.example .env
# Générer les secrets (POSTGRES_PASSWORD, BACKEND_SECRET_KEY…)
# puis remplir APP_DOMAIN=horizon.acreedconsulting.com
chmod 600 .env
```

### 2. Build + run

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Vérifier :

```bash
docker compose -f docker-compose.prod.yml ps
curl -sf http://127.0.0.1:8101/healthz    # → {"status":"alive"}
curl -sI http://127.0.0.1:8100/           # → HTTP/1.1 200
```

### 3. Vhost nginx

Fichier `/etc/nginx/sites-available/horizon.acreedconsulting.com` :

```nginx
server {
    listen 80;
    server_name horizon.acreedconsulting.com;

    location /api/ {
        proxy_pass http://127.0.0.1:8101;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 20M;
        proxy_read_timeout 180s;
        proxy_connect_timeout 10s;
    }

    location / {
        proxy_pass http://127.0.0.1:8100;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -sf /etc/nginx/sites-available/horizon.acreedconsulting.com \
           /etc/nginx/sites-enabled/horizon.acreedconsulting.com
sudo nginx -t && sudo systemctl reload nginx
```

### 4. TLS via certbot

```bash
sudo certbot --nginx -d horizon.acreedconsulting.com \
             --non-interactive --agree-tos --redirect
```

Certbot édite le vhost pour ajouter le bloc `listen 443 ssl` et installe un
timer systemd de renouvellement automatique.

### 5. Premier admin

L'endpoint `POST /api/bootstrap` est ouvert tant qu'aucun utilisateur n'existe
(il retourne 409 `L'amorçage est déjà effectué` après la création du premier
compte). Politique mot de passe : minimum 12 caractères.

```bash
curl -X POST https://horizon.acreedconsulting.com/api/bootstrap \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@acreedconsulting.com","password":"<password>","full_name":"Admin"}'
```

### 6. Smoke tests HTTPS

```bash
curl -sI https://horizon.acreedconsulting.com/          # 200, HTTP/2
curl -sI http://horizon.acreedconsulting.com/           # 301 → https
curl -s  https://horizon.acreedconsulting.com/api/me    # 401 sans session
```

## Pièges rencontrés

- **Migration alembic + enum PostgreSQL** : `sa.Enum` déclenche un second
  `CREATE TYPE` via `before_create` dans `op.create_table`, après le `.create()`
  explicite, ce qui casse la migration (rollback → DB vide). Fix : utiliser
  `postgresql.ENUM(..., create_type=False)` dans la migration.
- **StrEnum SQLAlchemy** : par défaut, SQLAlchemy sérialise le **nom** de
  l'énum (`"ADMIN"`) alors que le type Postgres attend la **valeur**
  (`"admin"`). Fix : `Enum(UserRole, values_callable=lambda e: [m.value for m in e])`
  sur la colonne.
- **Typage Vite** : `frontend/tsconfig.json` doit inclure `"vite/client"` dans
  `types` (sans quoi `import.meta.env` n'est pas typé et `tsc` échoue).

## Opérations courantes

```bash
# Logs live
docker compose -f docker-compose.prod.yml logs -f backend

# Redéploiement après pull
git pull
docker compose -f docker-compose.prod.yml up -d --build

# Sauvegarde DB (ponctuelle)
docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > backup-$(date +%F).sql.gz
```
