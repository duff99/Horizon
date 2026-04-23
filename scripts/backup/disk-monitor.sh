#!/usr/bin/env bash
# disk-monitor.sh — surveille l'espace disque du dossier backups.
#
# Si used% > 85% : loggue via `logger` (syslog) en daemon.alert + stdout.
# Retourne toujours les stats en JSON sur stdout pour que cron les capture.
#
# Exit code : 0 toujours (le monitoring ne fait pas planter le cron).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKUP_DIR="$ROOT_DIR/backups"

THRESHOLD=85

# df sur le dossier backups ; prend la partition qui l'héberge.
# -BG = en GB ; on parse la 2e ligne.
read -r FS SIZE USED AVAIL USEPCT MOUNT <<< "$(df -BG "$BACKUP_DIR" | awk 'NR==2')"

# USEPCT vaut '42%' — on enlève le '%'.
USED_PCT="${USEPCT%%%}"
SIZE_GB="${SIZE%G}"
USED_GB="${USED%G}"
AVAIL_GB="${AVAIL%G}"

STATUS="ok"
if (( USED_PCT > THRESHOLD )); then
  STATUS="alert"
  MSG="ALERT: disk at ${USED_PCT}% on $MOUNT (used ${USED_GB}GB / ${SIZE_GB}GB, avail ${AVAIL_GB}GB)"
  logger -p daemon.alert -t horizon-disk-monitor "$MSG"
  echo "$MSG" >&2
fi

# JSON sur stdout, compact.
printf '{"mount":"%s","filesystem":"%s","size_gb":%s,"used_gb":%s,"avail_gb":%s,"used_pct":%s,"threshold_pct":%s,"status":"%s"}\n' \
  "$MOUNT" "$FS" "$SIZE_GB" "$USED_GB" "$AVAIL_GB" "$USED_PCT" "$THRESHOLD" "$STATUS"

exit 0
