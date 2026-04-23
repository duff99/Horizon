#!/usr/bin/env bash
# backup-db.sh — pg_dump Postgres Horizon + manifest + entrée DB + rétention.
#
# Contexte : incident 2026-04-21 (Astreos) = perte de données suite à un
# `docker compose stop` sans backup. Ce script est invoqué soit par cron,
# soit manuellement, soit par `safe-stop.sh --pre-op` avant toute opération
# docker potentiellement destructive.
#
# Sortie : ./backups/horizon-<ISO>.dump (+ .sha256 + .manifest.json)
# DB : insère une ligne dans `backup_history` (running -> success/failed).
# Logs : stdout + ./logs/backup/backup-<ISO>.log (rétention 14j).
#
# Exit codes :
#   0 = OK
#   1 = pg_dump failed (ou pré-check échoué)
#   2 = checksum mismatch
#   3 = DB insert/update failed
#
# Flags :
#   --pre-op   : mode pré-opération (affiche "OK" si succès, exit 1 sinon)
#   --dry-run  : affiche les actions sans rien exécuter

set -euo pipefail

# ===== RÉSOLUTION DES CHEMINS =====
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKUP_DIR="$ROOT_DIR/backups"
LOG_DIR="$ROOT_DIR/logs/backup"

# ===== CONSTANTES =====
DB_CONTAINER="horizon-db-1"
DB_USER="tresorerie"
DB_NAME="tresorerie"
RETENTION_DAYS=30
LOG_RETENTION_DAYS=14
KEY_TABLES=(users entities transactions bank_accounts forecast_lines)

# ===== FLAGS =====
PRE_OP=false
DRY_RUN=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --pre-op) PRE_OP=true; shift ;;
    --dry-run) DRY_RUN=true; shift ;;
    -h|--help)
      grep -E '^# ' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) echo "Unknown flag: $1" >&2; exit 1 ;;
  esac
done

# ===== TIMESTAMP + PATHS =====
TS="$(date -u +%Y%m%dT%H%M%SZ)"
DUMP_PATH="$BACKUP_DIR/horizon-$TS.dump"
SHA_PATH="$DUMP_PATH.sha256"
MANIFEST_PATH="$DUMP_PATH.manifest.json"
LOG_PATH="$LOG_DIR/backup-$TS.log"

# ===== LOGGING =====
mkdir -p "$BACKUP_DIR" "$LOG_DIR"
log() {
  local msg="[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"
  if [[ "$DRY_RUN" == "true" ]]; then
    printf '%s\n' "$msg"
  else
    printf '%s\n' "$msg" | tee -a "$LOG_PATH"
  fi
}
err() { log "ERROR: $*" >&2; }

# ===== HELPERS =====
psql_exec() {
  docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -At "$@"
}

# Échappement SQL simple : double les quotes simples.
sql_quote() { printf "%s" "$1" | sed "s/'/''/g"; }

BACKUP_ROW_ID=""

mark_failed() {
  local reason="$1"
  local reason_esc
  reason_esc="$(sql_quote "$reason")"
  if [[ -n "$BACKUP_ROW_ID" ]]; then
    psql_exec -c "UPDATE backup_history
        SET status='failed',
            completed_at=now(),
            error_message='$reason_esc'
        WHERE id='$BACKUP_ROW_ID';" >/dev/null 2>&1 || \
      err "Impossible de marquer la ligne $BACKUP_ROW_ID en failed"
  fi
}

# ===== PRÉ-CHECK CONTAINER =====
precheck() {
  if ! docker ps --format '{{.Names}}' | grep -qx "$DB_CONTAINER"; then
    err "Container $DB_CONTAINER introuvable ou arrêté"
    return 1
  fi
  if ! docker exec "$DB_CONTAINER" pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
    err "Postgres pas prêt dans $DB_CONTAINER"
    return 1
  fi
}

# ===== DRY-RUN =====
if [[ "$DRY_RUN" == "true" ]]; then
  log "[dry-run] Actions prévues :"
  log "  - docker exec $DB_CONTAINER pg_dump ... > $DUMP_PATH"
  log "  - sha256sum $DUMP_PATH > $SHA_PATH"
  log "  - write manifest $MANIFEST_PATH"
  log "  - insert backup_history row"
  log "  - find $BACKUP_DIR -mtime +$RETENTION_DAYS -delete"
  exit 0
fi

# ===== PRE-OP MODE =====
# En mode pré-op, on fait tout le backup normal, mais on réduit la sortie
# à "OK" / "FAIL" pour un parsing trivial par safe-stop.sh.
if [[ "$PRE_OP" == "true" ]]; then
  log "== Mode pré-opération (backup avant docker op) =="
fi

# ===== LANCEMENT =====
log "== Backup Horizon DB (TS=$TS) =="
precheck || exit 1

# 1. Insert row backup_history (status=running).
log "-- Insert backup_history (running)"
DUMP_PATH_ESC="$(sql_quote "$DUMP_PATH")"
INSERT_SQL="INSERT INTO backup_history (status, file_path)
  VALUES ('running', '$DUMP_PATH_ESC')
  RETURNING id;"
if ! BACKUP_ROW_ID="$(psql_exec -c "$INSERT_SQL" | awk 'NR==1{print; exit}' | tr -d '[:space:]')"; then
  err "Insert backup_history a échoué"
  exit 3
fi
if [[ -z "$BACKUP_ROW_ID" ]]; then
  err "backup_history.id vide après insert — la table existe-t-elle ?"
  exit 3
fi
log "-- row_id=$BACKUP_ROW_ID"

# Trap : toute sortie anormale passe par mark_failed + message.
trap 'rc=$?; if [[ $rc -ne 0 ]]; then mark_failed "Exit $rc (step unknown)"; err "Abort exit=$rc"; fi' EXIT

# 2. pg_dump → fichier local.
log "-- pg_dump vers $DUMP_PATH"
if ! docker exec "$DB_CONTAINER" pg_dump \
    -U "$DB_USER" -d "$DB_NAME" \
    -Fc --no-owner --no-acl > "$DUMP_PATH"; then
  mark_failed "pg_dump a échoué"
  err "pg_dump KO"
  exit 1
fi
if [[ ! -s "$DUMP_PATH" ]]; then
  mark_failed "Dump vide ou absent"
  err "Dump vide"
  exit 1
fi
SIZE_BYTES="$(stat -c%s "$DUMP_PATH")"
log "-- dump size=$SIZE_BYTES bytes"

# 3. Checksum SHA256.
log "-- sha256sum"
if ! (cd "$BACKUP_DIR" && sha256sum "$(basename "$DUMP_PATH")" > "$(basename "$SHA_PATH")"); then
  mark_failed "sha256 write failed"
  err "sha256sum KO"
  exit 2
fi
SHA256_HEX="$(awk '{print $1; exit}' "$SHA_PATH")"
if [[ ${#SHA256_HEX} -ne 64 ]]; then
  mark_failed "sha256 format invalide"
  err "SHA256 invalide: $SHA256_HEX"
  exit 2
fi
log "-- sha256=$SHA256_HEX"

# 4. Row counts sur tables clés.
log "-- row counts"
ROW_COUNTS_JSON="{"
first=true
for tbl in "${KEY_TABLES[@]}"; do
  cnt="$(psql_exec -c "SELECT count(*) FROM $tbl;" | tr -d '[:space:]')"
  # On accepte 0 mais pas vide (table absente).
  if [[ -z "$cnt" ]]; then
    mark_failed "Impossible de compter la table $tbl"
    err "count $tbl KO"
    exit 1
  fi
  if [[ "$first" == "true" ]]; then
    first=false
  else
    ROW_COUNTS_JSON+=","
  fi
  ROW_COUNTS_JSON+="\"$tbl\":$cnt"
done
ROW_COUNTS_JSON+="}"
log "-- row_counts=$ROW_COUNTS_JSON"

# 5. Version Postgres.
PG_VERSION="$(psql_exec -c "SELECT current_setting('server_version');" | tr -d '[:space:]')"

# 6. Écrire le manifest JSON.
log "-- write manifest"
cat > "$MANIFEST_PATH" <<EOF
{
  "timestamp": "$TS",
  "file_path": "$DUMP_PATH",
  "size_bytes": $SIZE_BYTES,
  "sha256": "$SHA256_HEX",
  "postgres_version": "$PG_VERSION",
  "row_counts": $ROW_COUNTS_JSON,
  "backup_history_id": "$BACKUP_ROW_ID"
}
EOF

# 7. Update backup_history en success.
log "-- Update backup_history (success)"
ROW_COUNTS_ESC="$(sql_quote "$ROW_COUNTS_JSON")"
UPDATE_SQL="UPDATE backup_history
  SET status='success',
      completed_at=now(),
      size_bytes=$SIZE_BYTES,
      sha256='$SHA256_HEX',
      row_counts_json='$ROW_COUNTS_ESC'::jsonb
  WHERE id='$BACKUP_ROW_ID';"
if ! psql_exec -c "$UPDATE_SQL" >/dev/null; then
  err "Update backup_history a échoué (backup ok mais traçabilité cassée)"
  exit 3
fi

# 8. Rétention 30j sur les fichiers backup + 14j sur les logs.
log "-- cleanup (>$RETENTION_DAYS jours)"
find "$BACKUP_DIR" -maxdepth 1 -type f \
  \( -name 'horizon-*.dump' -o -name 'horizon-*.dump.sha256' -o -name 'horizon-*.dump.manifest.json' \) \
  -mtime +$RETENTION_DAYS -print -delete || true
find "$LOG_DIR" -maxdepth 1 -type f -name 'backup-*.log' \
  -mtime +$LOG_RETENTION_DAYS -print -delete || true

log "== DONE =="

# Désarme le trap (succès).
trap - EXIT

if [[ "$PRE_OP" == "true" ]]; then
  echo "OK"
fi

exit 0
