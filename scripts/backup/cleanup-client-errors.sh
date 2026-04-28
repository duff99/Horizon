#!/usr/bin/env bash
# cleanup-client-errors.sh — supprime les rows client_errors > 30 jours.
#
# Lancé par cron (1x/jour, déclenché par le crontab horizon-backup).
# Rétention 30j validée 2026-04-28.

set -euo pipefail

DB_CONTAINER="horizon-db-1"
DB_USER="tresorerie"
DB_NAME="tresorerie"
RETENTION_DAYS=30

log() { printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }

if ! docker ps --format '{{.Names}}' | grep -qx "$DB_CONTAINER"; then
  log "Container $DB_CONTAINER absent — abort"
  exit 1
fi

DELETED=$(docker exec -i "$DB_CONTAINER" psql -q -U "$DB_USER" -d "$DB_NAME" -At -c "
  DELETE FROM client_errors
  WHERE occurred_at < now() - interval '$RETENTION_DAYS days'
  RETURNING 1;
" 2>&1 | grep -c "^1$" || true)

log "client_errors cleanup : $DELETED rows supprimées (> ${RETENTION_DAYS}j)"
