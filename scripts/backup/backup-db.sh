#!/usr/bin/env bash
# backup-db.sh — pg_dump Postgres Horizon + tar volume imports + manifest + DB + rétention.
#
# Contexte : incident 2026-04-21 (Astreos) = perte de données suite à un
# `docker compose stop` sans backup. Ce script est invoqué soit par cron,
# soit manuellement, soit par `safe-stop.sh --pre-op` avant toute opération
# docker potentiellement destructive.
#
# Sortie :
#   ./backups/horizon-<ISO>.dump            (pg_dump custom)
#   ./backups/horizon-<ISO>.dump.sha256
#   ./backups/horizon-<ISO>.imports.tar.gz  (volume horizon_import_storage)
#   ./backups/horizon-<ISO>.imports.tar.gz.sha256
#   ./backups/horizon-<ISO>.dump.manifest.json (référence les 2 fichiers)
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
IMPORTS_VOLUME="horizon_import_storage"
RETENTION_DAYS=30
LOG_RETENTION_DAYS=14
KEY_TABLES=(users entities transactions bank_accounts forecast_lines)

# ===== FLAGS =====
PRE_OP=false
DRY_RUN=false
ROW_ID=""              # si fourni : adopte une row pending au lieu d'en créer une
TYPE="scheduled"       # défaut : cron quotidien. Autres : manual, pre-op, restore-test
while [[ $# -gt 0 ]]; do
  case "$1" in
    --pre-op) PRE_OP=true; TYPE="pre-op"; shift ;;
    --dry-run) DRY_RUN=true; shift ;;
    --row-id) ROW_ID="$2"; shift 2 ;;
    --row-id=*) ROW_ID="${1#*=}"; shift ;;
    --type) TYPE="$2"; shift 2 ;;
    --type=*) TYPE="${1#*=}"; shift ;;
    -h|--help)
      grep -E '^# ' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) echo "Unknown flag: $1" >&2; exit 1 ;;
  esac
done

# Validation type (en sync avec ck_backup_history_type)
case "$TYPE" in
  scheduled|manual|pre-op|restore-test) ;;
  *) echo "Invalid --type: $TYPE (expected: scheduled|manual|pre-op|restore-test)" >&2; exit 1 ;;
esac

# ===== TIMESTAMP + PATHS =====
TS="$(date -u +%Y%m%dT%H%M%SZ)"
DUMP_PATH="$BACKUP_DIR/horizon-$TS.dump"
SHA_PATH="$DUMP_PATH.sha256"
IMPORTS_PATH="$BACKUP_DIR/horizon-$TS.imports.tar.gz"
IMPORTS_SHA_PATH="$IMPORTS_PATH.sha256"
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
  local step="${CURRENT_STEP:-}"
  local reason_esc step_esc
  reason_esc="$(sql_quote "$reason")"
  step_esc="$(sql_quote "$step")"
  if [[ -n "$BACKUP_ROW_ID" ]]; then
    psql_exec -c "UPDATE backup_history
        SET status='failed',
            completed_at=now(),
            error_message='$reason_esc',
            error_step='$step_esc'
        WHERE id='$BACKUP_ROW_ID';" >/dev/null 2>&1 || \
      err "Impossible de marquer la ligne $BACKUP_ROW_ID en failed"
  fi
}

# CURRENT_STEP : tracker pour l'étape qui plante (lu par mark_failed).
CURRENT_STEP="init"

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
  log "  - tar -czf $IMPORTS_PATH (volume $IMPORTS_VOLUME)"
  log "  - sha256sum $IMPORTS_PATH > $IMPORTS_SHA_PATH"
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

# 1. Soit on adopte une row pré-créée (déclenchement UI via trigger watcher),
#    soit on en crée une nouvelle (cron quotidien, manuel CLI).
CURRENT_STEP="register"
DUMP_PATH_ESC="$(sql_quote "$DUMP_PATH")"
TYPE_ESC="$(sql_quote "$TYPE")"
if [[ -n "$ROW_ID" ]]; then
  log "-- Adopte row pending $ROW_ID (running, type=$TYPE)"
  ROW_ID_ESC="$(sql_quote "$ROW_ID")"
  if ! psql_exec -c "UPDATE backup_history
      SET status='running', started_at=now(), file_path='$DUMP_PATH_ESC'
      WHERE id='$ROW_ID_ESC' AND status='pending';" >/dev/null; then
    err "Update backup_history (adopt) a échoué"
    exit 3
  fi
  BACKUP_ROW_ID="$ROW_ID"
else
  log "-- Insert backup_history (running, type=$TYPE)"
  INSERT_SQL="INSERT INTO backup_history (status, type, file_path)
    VALUES ('running', '$TYPE_ESC', '$DUMP_PATH_ESC')
    RETURNING id;"
  if ! BACKUP_ROW_ID="$(psql_exec -c "$INSERT_SQL" | awk 'NR==1{print; exit}' | tr -d '[:space:]')"; then
    err "Insert backup_history a échoué"
    exit 3
  fi
  if [[ -z "$BACKUP_ROW_ID" ]]; then
    err "backup_history.id vide après insert — la table existe-t-elle ?"
    exit 3
  fi
fi
log "-- row_id=$BACKUP_ROW_ID"

# Trap : toute sortie anormale passe par mark_failed + message.
trap 'rc=$?; if [[ $rc -ne 0 ]]; then mark_failed "Exit $rc (step unknown)"; err "Abort exit=$rc"; fi' EXIT

# 2. pg_dump → fichier local.
CURRENT_STEP="pg_dump"
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
CURRENT_STEP="sha256_dump"
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
CURRENT_STEP="row_counts"
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

# 5bis. Tar du volume Docker `horizon_import_storage` (PDF/CSV importés).
# Le volume est monté en lecture par root sous /var/lib/docker/volumes/<vol>/_data.
# On tar via `docker run --rm -v <vol>:/src` pour éviter d'avoir à élever les
# privilèges sur le host (le script tourne déjà en root via cron, mais ça
# permet aussi un usage manuel sans sudo si le user est dans le groupe docker).
CURRENT_STEP="tar_imports"
log "-- tar volume $IMPORTS_VOLUME"
if ! docker volume inspect "$IMPORTS_VOLUME" >/dev/null 2>&1; then
  mark_failed "Volume $IMPORTS_VOLUME introuvable"
  err "Volume $IMPORTS_VOLUME absent"
  exit 1
fi
if ! docker run --rm \
    -v "$IMPORTS_VOLUME":/src:ro \
    -v "$BACKUP_DIR":/dst \
    alpine:3.20 \
    tar -czf "/dst/$(basename "$IMPORTS_PATH")" -C /src . 2>>"$LOG_PATH"; then
  mark_failed "tar volume imports a échoué"
  err "tar imports KO"
  exit 1
fi
if [[ ! -s "$IMPORTS_PATH" ]]; then
  mark_failed "Tar imports vide"
  err "Tar imports vide"
  exit 1
fi
IMPORTS_SIZE_BYTES="$(stat -c%s "$IMPORTS_PATH")"
log "-- imports size=$IMPORTS_SIZE_BYTES bytes"

CURRENT_STEP="sha256_imports"
log "-- sha256 imports"
if ! (cd "$BACKUP_DIR" && sha256sum "$(basename "$IMPORTS_PATH")" > "$(basename "$IMPORTS_SHA_PATH")"); then
  mark_failed "sha256 imports write failed"
  err "sha256sum imports KO"
  exit 2
fi
IMPORTS_SHA256_HEX="$(awk '{print $1; exit}' "$IMPORTS_SHA_PATH")"
if [[ ${#IMPORTS_SHA256_HEX} -ne 64 ]]; then
  mark_failed "sha256 imports format invalide"
  err "SHA256 imports invalide: $IMPORTS_SHA256_HEX"
  exit 2
fi
log "-- sha256 imports=$IMPORTS_SHA256_HEX"

# 6. Écrire le manifest JSON (référence DB dump + imports tar).
CURRENT_STEP="manifest"
log "-- write manifest"
cat > "$MANIFEST_PATH" <<EOF
{
  "timestamp": "$TS",
  "file_path": "$DUMP_PATH",
  "size_bytes": $SIZE_BYTES,
  "sha256": "$SHA256_HEX",
  "postgres_version": "$PG_VERSION",
  "row_counts": $ROW_COUNTS_JSON,
  "imports_file": "$IMPORTS_PATH",
  "imports_size_bytes": $IMPORTS_SIZE_BYTES,
  "imports_sha256": "$IMPORTS_SHA256_HEX",
  "imports_volume": "$IMPORTS_VOLUME",
  "backup_history_id": "$BACKUP_ROW_ID"
}
EOF

# 7. Update backup_history en success.
CURRENT_STEP="update_row_success"
log "-- Update backup_history (success)"
ROW_COUNTS_ESC="$(sql_quote "$ROW_COUNTS_JSON")"
UPDATE_SQL="UPDATE backup_history
  SET status='success',
      completed_at=now(),
      size_bytes=$SIZE_BYTES,
      sha256='$SHA256_HEX',
      imports_size_bytes=$IMPORTS_SIZE_BYTES,
      imports_sha256='$IMPORTS_SHA256_HEX',
      row_counts_json='$ROW_COUNTS_ESC'::jsonb
  WHERE id='$BACKUP_ROW_ID';"
if ! psql_exec -c "$UPDATE_SQL" >/dev/null; then
  err "Update backup_history a échoué (backup ok mais traçabilité cassée)"
  exit 3
fi

# 8. Rétention 30j sur les fichiers backup + 14j sur les logs.
log "-- cleanup (>$RETENTION_DAYS jours)"
find "$BACKUP_DIR" -maxdepth 1 -type f \
  \( -name 'horizon-*.dump' \
   -o -name 'horizon-*.dump.sha256' \
   -o -name 'horizon-*.dump.manifest.json' \
   -o -name 'horizon-*.imports.tar.gz' \
   -o -name 'horizon-*.imports.tar.gz.sha256' \) \
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
