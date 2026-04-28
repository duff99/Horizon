#!/usr/bin/env bash
# verify-restore.sh — test de restauration du dernier backup dans un container éphémère.
#
# Prend le dump le plus récent (par mtime) + son manifest, lance un Postgres 16
# éphémère, pg_restore, compare les row_counts avec ceux du manifest. Si OK,
# met à jour backup_history.verified_at (en utilisant backup_history_id du manifest)
# et met status='verified'.
#
# Exit codes : 0 = OK, non-zero sinon.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKUP_DIR="$ROOT_DIR/backups"

DB_CONTAINER="horizon-db-1"
DB_USER="tresorerie"
DB_NAME="tresorerie"
VERIFY_CONTAINER="horizon-verify-$$"
VERIFY_PASSWORD="verify-$(date +%s)"
PG_IMAGE="postgres:16-alpine"

# Flag --row-id : si fourni, on met à jour cette row (au lieu de créer/chercher
# par manifest) → utilisé par le trigger watcher quand l'UI demande "Lancer un
# test de restore". Cette row est de type 'restore-test' (créée pending par
# l'API, adoptée running ici, success/failed à la fin).
ROW_ID=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --row-id) ROW_ID="$2"; shift 2 ;;
    --row-id=*) ROW_ID="${1#*=}"; shift ;;
    -h|--help)
      grep -E '^# ' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) echo "Unknown flag: $1" >&2; exit 1 ;;
  esac
done

log() { printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
err() { log "ERROR: $*" >&2; }

# Si on a un ROW_ID, on l'adopte en running au démarrage et on marque
# l'issue à la sortie (success ou failed) — pour que l'UI voie le statut
# se mettre à jour.
mark_test_failed() {
  local reason="$1"
  local reason_esc step_esc
  reason_esc="$(printf "%s" "$reason" | sed "s/'/''/g")"
  step_esc="$(printf "%s" "${CURRENT_STEP:-}" | sed "s/'/''/g")"
  if [[ -n "$ROW_ID" ]]; then
    docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -At -c \
      "UPDATE backup_history
       SET status='failed', completed_at=now(),
           error_message='$reason_esc', error_step='$step_esc'
       WHERE id='$ROW_ID';" >/dev/null 2>&1 || true
  fi
}
CURRENT_STEP="init"

if [[ -n "$ROW_ID" ]]; then
  ROW_ID_ESC="$(printf "%s" "$ROW_ID" | sed "s/'/''/g")"
  docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -At -c \
    "UPDATE backup_history SET status='running', started_at=now()
     WHERE id='$ROW_ID_ESC' AND status='pending';" >/dev/null 2>&1 || \
    err "Adopt row $ROW_ID en running KO (non-fatal)"
  trap 'rc=$?; if [[ $rc -ne 0 ]]; then mark_test_failed "Exit $rc à étape ${CURRENT_STEP:-?}"; fi; docker rm -f "$VERIFY_CONTAINER" >/dev/null 2>&1 || true' EXIT
fi

cleanup() {
  docker rm -f "$VERIFY_CONTAINER" >/dev/null 2>&1 || true
}
trap cleanup EXIT

# Échappement SQL simple.
sql_quote() { printf "%s" "$1" | sed "s/'/''/g"; }

# 1. Localiser le backup le plus récent.
log "Localiser le dernier dump dans $BACKUP_DIR"
LATEST_DUMP="$(find "$BACKUP_DIR" -maxdepth 1 -name 'horizon-*.dump' -type f -printf '%T@ %p\n' 2>/dev/null \
  | sort -nr | awk 'NR==1 {print $2}')"
if [[ -z "$LATEST_DUMP" ]]; then
  err "Aucun dump .dump trouvé dans $BACKUP_DIR"
  exit 1
fi
MANIFEST="$LATEST_DUMP.manifest.json"
SHA_FILE="$LATEST_DUMP.sha256"
if [[ ! -f "$MANIFEST" || ! -f "$SHA_FILE" ]]; then
  err "Manifest ou sha256 absent à côté de $LATEST_DUMP"
  exit 1
fi
log "Dump: $LATEST_DUMP"

# 2. Vérifier SHA256 du dump DB.
log "Vérif SHA256 dump"
if ! (cd "$BACKUP_DIR" && sha256sum -c "$(basename "$SHA_FILE")" >/dev/null); then
  err "SHA256 mismatch sur $LATEST_DUMP"
  exit 2
fi

# 2bis. Vérifier le tar imports si présent (manifest le référence).
IMPORTS_FILE="$(python3 -c "
import json
m = json.load(open('$MANIFEST'))
print(m.get('imports_file', ''))
" 2>/dev/null || echo "")"
IMPORTS_SHA="$(python3 -c "
import json
m = json.load(open('$MANIFEST'))
print(m.get('imports_sha256', ''))
" 2>/dev/null || echo "")"
if [[ -n "$IMPORTS_FILE" && -f "$IMPORTS_FILE" ]]; then
  log "Vérif SHA256 imports"
  IMPORTS_SHA_PATH="$IMPORTS_FILE.sha256"
  if [[ ! -f "$IMPORTS_SHA_PATH" ]]; then
    err "Fichier sha256 imports absent : $IMPORTS_SHA_PATH"
    exit 2
  fi
  if ! (cd "$BACKUP_DIR" && sha256sum -c "$(basename "$IMPORTS_SHA_PATH")" >/dev/null); then
    err "SHA256 mismatch sur $IMPORTS_FILE"
    exit 2
  fi
  log "Vérif tar list (intégrité archive)"
  if ! tar -tzf "$IMPORTS_FILE" >/dev/null 2>&1; then
    err "Archive imports corrompue (tar -tzf KO)"
    exit 2
  fi
  ENTRIES_COUNT="$(tar -tzf "$IMPORTS_FILE" | wc -l)"
  log "  imports archive : $ENTRIES_COUNT entrées OK"
else
  log "(pas de tar imports dans le manifest — ancien backup ?)"
fi

# 3. Extraire backup_history_id + row_counts du manifest (sans jq pour simplicité).
BACKUP_ROW_ID="$(grep -oE '"backup_history_id"[[:space:]]*:[[:space:]]*"[^"]+"' "$MANIFEST" \
  | sed -E 's/.*"([^"]+)"$/\1/')"
ROW_COUNTS_JSON="$(python3 -c "
import json, sys
m = json.load(open('$MANIFEST'))
print(json.dumps(m.get('row_counts', {})))
")"
log "backup_history_id=$BACKUP_ROW_ID"
log "expected row_counts=$ROW_COUNTS_JSON"

# 4. Lancer container Postgres éphémère.
log "Spawn container $VERIFY_CONTAINER ($PG_IMAGE)"
docker run -d --rm \
  --name "$VERIFY_CONTAINER" \
  -e POSTGRES_PASSWORD="$VERIFY_PASSWORD" \
  -e POSTGRES_USER="$DB_USER" \
  -e POSTGRES_DB="$DB_NAME" \
  "$PG_IMAGE" >/dev/null

# 5. Attendre pg_isready (max 60s).
log "Wait for ready..."
for _ in $(seq 1 60); do
  if docker exec "$VERIFY_CONTAINER" pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
if ! docker exec "$VERIFY_CONTAINER" pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
  err "Container $VERIFY_CONTAINER pas healthy après 60s"
  exit 3
fi

# 6. Copier le dump dans le container puis pg_restore.
log "Copy dump dans le container"
docker cp "$LATEST_DUMP" "$VERIFY_CONTAINER:/tmp/dump.pgdump"

log "pg_restore"
# --no-owner --no-acl car on a dumpé sans owner.
# --clean --if-exists : no-op sur base fraîche, mais robuste.
# On accepte les warnings non-fatals mais on vérifie le row_counts ensuite.
docker exec "$VERIFY_CONTAINER" pg_restore \
  -U "$DB_USER" -d "$DB_NAME" \
  --no-owner --no-acl \
  /tmp/dump.pgdump 2>&1 | tail -20 || true

# 7. Comparer row_counts.
log "Vérif row_counts"
verify_ok=true
for tbl_n in $(python3 -c "
import json
for t, n in json.loads('''$ROW_COUNTS_JSON''').items():
    print(f'{t}={n}')
"); do
  tbl="${tbl_n%%=*}"
  expected="${tbl_n##*=}"
  actual="$(docker exec "$VERIFY_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -At \
    -c "SELECT count(*) FROM $tbl;" 2>/dev/null | tr -d '[:space:]')"
  if [[ "$actual" != "$expected" ]]; then
    err "Mismatch $tbl : restored=$actual, manifest=$expected"
    verify_ok=false
  else
    log "  $tbl : $actual OK"
  fi
done

if [[ "$verify_ok" != "true" ]]; then
  err "Verify-restore FAILED"
  exit 4
fi

# 8. Update backup_history (status=verified + verified_at=now()) sur la prod
#    pour la row du backup vérifié (issue du manifest).
if [[ -n "$BACKUP_ROW_ID" ]]; then
  log "Update backup_history $BACKUP_ROW_ID en verified"
  ID_ESC="$(sql_quote "$BACKUP_ROW_ID")"
  docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c \
    "UPDATE backup_history SET status='verified', verified_at=now() WHERE id='$ID_ESC';" \
    >/dev/null || err "Impossible de marquer verified en DB prod (non-fatal)"
fi

# 9. Si on a une row de type 'restore-test' déclenchée par UI, on la marque
#    success (le verify a réussi). C'est cette row qui est observée par l'UI
#    pour informer l'utilisateur "test de restore terminé avec succès".
if [[ -n "$ROW_ID" ]]; then
  ROW_ID_ESC="$(sql_quote "$ROW_ID")"
  docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c \
    "UPDATE backup_history SET status='success', completed_at=now()
     WHERE id='$ROW_ID_ESC';" \
    >/dev/null || err "Impossible de marquer la row UI en success (non-fatal)"
fi

log "== VERIFY OK =="
exit 0
