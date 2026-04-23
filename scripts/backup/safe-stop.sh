#!/usr/bin/env bash
# safe-stop.sh — wrapper OBLIGATOIRE pour docker compose stop/restart/down.
#
# Avant toute opération docker potentiellement destructive, on lance un
# backup pré-opération. Si le backup échoue, on refuse l'opération.
#
# Raison : incident 2026-04-21 (Astreos — perte totale après `docker compose stop`).
#
# Usage :
#   ./scripts/backup/safe-stop.sh stop
#   ./scripts/backup/safe-stop.sh restart
#   ./scripts/backup/safe-stop.sh down
#   ./scripts/backup/safe-stop.sh up -d --build    (OK aussi, ne fait jamais de mal de backup avant)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker-compose.prod.yml"

if [[ $# -eq 0 ]]; then
  echo "Usage: $0 <docker compose action> [args...]" >&2
  echo "  ex: $0 stop | restart | down | up -d" >&2
  exit 1
fi

echo "[safe-stop] Backup pré-opération obligatoire avant '$*'..."
if ! "$SCRIPT_DIR/backup-db.sh" --pre-op; then
  echo "[safe-stop] Backup ÉCHOUÉ — refus d'exécuter '$*'." >&2
  exit 1
fi

echo "[safe-stop] Backup OK. Exécution : docker compose -f $COMPOSE_FILE $*"
cd "$ROOT_DIR"
exec docker compose -f "$COMPOSE_FILE" "$@"
