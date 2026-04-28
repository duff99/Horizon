#!/usr/bin/env bash
# install-backup-system.sh — installe (ou réaligne) le système de backup Horizon.
#
# Idempotent : peut être relancé à volonté. Ne supprime pas les configs existantes,
# mais vérifie/corrige permissions + écrase cron et logrotate.
#
# Usage : sudo ./deploy/install-backup-system.sh
#
# Effets :
#   - chmod 755 sur scripts/backup/*.sh
#   - /etc/horizon-backup.env créé (vide, à remplir) si absent — chmod 600 root
#   - /etc/cron.d/horizon-backup écrasé depuis deploy/horizon-backup.cron — chmod 644
#   - /etc/logrotate.d/horizon-backup écrasé depuis deploy/horizon-backup.logrotate
#   - touch + chmod 640 sur /var/log/horizon-{backup,verify,disk}.log
#   - tente un cron RELOAD (pas obligatoire — cron détecte automatiquement /etc/cron.d/)
#
# Rappel : le off-site n'est pas géré ici, les variables HORIZON_OFFSITE_* dans
# /etc/horizon-backup.env restent vides tant que l'utilisateur n'a pas choisi
# son fournisseur (Cloudflare R2, Backblaze B2, Azure Blob…).

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Ce script doit être lancé en root : sudo $0" >&2
  exit 1
fi

REPO_ROOT="/srv/prod/tools/horizon"
DEPLOY_DIR="$REPO_ROOT/deploy"
SCRIPTS_DIR="$REPO_ROOT/scripts/backup"

if [[ ! -d "$SCRIPTS_DIR" ]]; then
  echo "ERROR: $SCRIPTS_DIR introuvable. Le repo est-il bien à $REPO_ROOT ?" >&2
  exit 1
fi

echo "== Permissions scripts =="
for script in backup-db.sh verify-restore.sh disk-monitor.sh safe-stop.sh; do
  if [[ -f "$SCRIPTS_DIR/$script" ]]; then
    chmod 755 "$SCRIPTS_DIR/$script"
    echo "  chmod 755 $SCRIPTS_DIR/$script"
  else
    echo "  WARN: $SCRIPTS_DIR/$script introuvable"
  fi
done

echo "== /etc/horizon-backup.env =="
if [[ ! -f /etc/horizon-backup.env ]]; then
  if [[ -f "$DEPLOY_DIR/horizon-backup.env.example" ]]; then
    cp "$DEPLOY_DIR/horizon-backup.env.example" /etc/horizon-backup.env
    chmod 600 /etc/horizon-backup.env
    chown root:root /etc/horizon-backup.env
    echo "  Créé depuis le template — à compléter quand l'off-site sera décidé."
  else
    echo "  ERROR: template $DEPLOY_DIR/horizon-backup.env.example absent" >&2
    exit 1
  fi
else
  # On ne touche pas au contenu, juste les droits.
  chmod 600 /etc/horizon-backup.env
  chown root:root /etc/horizon-backup.env
  echo "  Existe déjà — droits resserrés à 600 root:root, contenu inchangé."
fi

echo "== /etc/cron.d/horizon-backup =="
cp "$DEPLOY_DIR/horizon-backup.cron" /etc/cron.d/horizon-backup
chmod 644 /etc/cron.d/horizon-backup
chown root:root /etc/cron.d/horizon-backup
echo "  Installé depuis $DEPLOY_DIR/horizon-backup.cron"

echo "== /etc/logrotate.d/horizon-backup =="
cp "$DEPLOY_DIR/horizon-backup.logrotate" /etc/logrotate.d/horizon-backup
chmod 644 /etc/logrotate.d/horizon-backup
chown root:root /etc/logrotate.d/horizon-backup
echo "  Installé depuis $DEPLOY_DIR/horizon-backup.logrotate"

echo "== Logs (/var/log/horizon-*.log) =="
for logf in /var/log/horizon-backup.log /var/log/horizon-verify.log /var/log/horizon-disk.log; do
  touch "$logf"
  chmod 640 "$logf"
  chown root:root "$logf"
  echo "  $logf prêt (640 root:root)"
done

echo "== Validation logrotate (dry-run) =="
if logrotate -d /etc/logrotate.d/horizon-backup >/dev/null 2>&1; then
  echo "  OK"
else
  echo "  WARN: logrotate -d signale un souci, vérifier manuellement :"
  echo "        logrotate -d /etc/logrotate.d/horizon-backup"
fi

echo "== Validation cron =="
if [[ -x /etc/init.d/cron ]] || systemctl is-active --quiet cron 2>/dev/null; then
  echo "  service cron actif (les changements de /etc/cron.d/ sont détectés automatiquement)"
else
  echo "  WARN: cron ne semble pas actif — démarrer avec : systemctl start cron"
fi

cat <<EOF

Installation terminée.

Prochaines étapes manuelles :
  1. Vérifier le contenu de /etc/horizon-backup.env (sudo nano /etc/horizon-backup.env)
  2. Lancer un backup manuel pour valider :
       cd $REPO_ROOT && ./scripts/backup/backup-db.sh
  3. Vérifier le verify-restore :
       cd $REPO_ROOT && sudo ./scripts/backup/verify-restore.sh
  4. Off-site : voir deploy/horizon-backup.env.example (rclone ou azcopy)
EOF
