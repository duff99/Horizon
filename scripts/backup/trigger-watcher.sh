#!/usr/bin/env bash
# trigger-watcher.sh — surveille /var/lib/horizon-backup-triggers et exécute
# les opérations demandées par la page UI Sauvegardes.
#
# Architecture (option B — isolation backend↔hôte) :
#   - Le backend FastAPI (containerisé, non-root) dépose un fichier JSON
#     <uuid>.json dans /data/triggers (volume Docker bind-mounté sur l'hôte
#     à /var/lib/horizon-backup-triggers).
#   - Ce script (côté hôte, root, lancé par systemd) poll ce dossier toutes
#     les 2 secondes, traite les triggers, supprime les fichiers consommés.
#
# Format trigger : {"row_id": "<uuid>", "type": "manual" | "restore-test"}
#
# Le script tourne en boucle infinie ; relancé par systemd Restart=on-failure.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
TRIGGER_DIR="${HORIZON_TRIGGER_DIR:-/var/lib/horizon-backup-triggers}"
POLL_SECONDS=2
LOG_PREFIX="[trigger-watcher]"

log() { printf '%s %s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$LOG_PREFIX" "$*"; }
err() { log "ERROR: $*" >&2; }

mkdir -p "$TRIGGER_DIR"
chmod 770 "$TRIGGER_DIR" 2>/dev/null || true

log "Démarrage. Watch=$TRIGGER_DIR poll=${POLL_SECONDS}s"

extract_field() {
  # extract_field <file> <key> → valeur (ou vide), parsing JSON simple regex.
  # Évite la dépendance jq. Le format est contrôlé côté backend (Pydantic).
  local file="$1" key="$2"
  grep -oE "\"$key\"[[:space:]]*:[[:space:]]*\"[^\"]+\"" "$file" 2>/dev/null \
    | sed -E 's/.*"([^"]+)"$/\1/' | head -n1
}

uuid_re='^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'

process_trigger() {
  local file="$1"
  local row_id type
  row_id="$(extract_field "$file" "row_id")"
  type="$(extract_field "$file" "type")"

  if ! [[ "$row_id" =~ $uuid_re ]]; then
    err "Trigger $file : row_id invalide ($row_id) — fichier supprimé"
    rm -f "$file"
    return
  fi

  case "$type" in
    manual)
      log "Exec backup-db.sh --row-id $row_id --type manual"
      "$ROOT_DIR/scripts/backup/backup-db.sh" --row-id "$row_id" --type manual \
        >>/var/log/horizon-backup.log 2>&1 \
        && log "OK row=$row_id" \
        || err "backup-db.sh KO row=$row_id (cf /var/log/horizon-backup.log)"
      ;;
    restore-test)
      log "Exec verify-restore.sh --row-id $row_id"
      "$ROOT_DIR/scripts/backup/verify-restore.sh" --row-id "$row_id" \
        >>/var/log/horizon-verify.log 2>&1 \
        && log "OK row=$row_id" \
        || err "verify-restore.sh KO row=$row_id (cf /var/log/horizon-verify.log)"
      ;;
    *)
      err "Trigger $file : type non supporté ($type) — fichier supprimé"
      ;;
  esac
  rm -f "$file"
}

while true; do
  shopt -s nullglob
  for trigger in "$TRIGGER_DIR"/*.json; do
    process_trigger "$trigger"
  done
  shopt -u nullglob
  sleep "$POLL_SECONDS"
done
