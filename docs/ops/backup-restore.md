# Backup & restore — Horizon

> Contexte : suite à la perte de données Astreos du 2026-04-21 (docker compose stop sans backup),
> Horizon dispose d'une chaîne de backup rigoureuse avec traçabilité DB et test de round-trip hebdomadaire.

## Emplacements

- Scripts : `scripts/backup/` (`backup-db.sh`, `safe-stop.sh`, `verify-restore.sh`, `disk-monitor.sh`)
- Backups locaux : `backups/horizon-<ISO>.dump` (+ `.sha256`, `.manifest.json`) — **gitignored**
- Logs par run : `logs/backup/backup-<ISO>.log` — **gitignored**
- Traçabilité DB : table `backup_history` (UUID, status, sha256, row_counts_json, verified_at)
- Cron template : `deploy/horizon-backup.cron` (pas installé automatiquement)

## Backup manuel

```bash
cd /srv/prod/tools/horizon
./scripts/backup/backup-db.sh
```

Sortie attendue : un fichier `backups/horizon-<TS>.dump` + `.sha256` + `.manifest.json`, et une ligne
`backup_history` avec `status='success'`.

Flags :
- `--dry-run` : affiche ce qui serait fait, sans rien exécuter.
- `--pre-op` : mode silencieux pour `safe-stop.sh` (affiche "OK" à la fin ou sort en erreur).

## `safe-stop.sh` — arrêter Horizon sans risque

**Règle absolue** : tout `docker compose stop | restart | down` passe par ce wrapper.

```bash
./scripts/backup/safe-stop.sh restart
./scripts/backup/safe-stop.sh stop
./scripts/backup/safe-stop.sh down
```

Le wrapper lance un backup pré-opération ; si le backup échoue, l'opération docker est **refusée**.

## Restauration depuis un dump

1. Vérifier l'intégrité SHA256 avant restore :
   ```bash
   cd backups
   sha256sum -c horizon-<TS>.dump.sha256
   ```

2. Cas nominal — restauration sur la DB live (attention, remplace des données) :
   ```bash
   # 1. Arrêter le backend pour éviter les écritures concurrentes
   docker stop horizon-backend-1

   # 2. Vider la DB (ou la recréer)
   docker exec -it horizon-db-1 psql -U tresorerie -d postgres -c \
     "DROP DATABASE tresorerie WITH (FORCE); CREATE DATABASE tresorerie OWNER tresorerie;"

   # 3. Restaurer
   docker exec -i horizon-db-1 pg_restore -U tresorerie -d tresorerie \
     --no-owner --no-acl < backups/horizon-<TS>.dump

   # 4. Relancer le backend
   docker start horizon-backend-1
   ```

3. Cas "test" — restauration dans un container éphémère : voir `verify-restore.sh`.

## Test de restauration (vérification périodique)

```bash
./scripts/backup/verify-restore.sh
```

Ce que fait le script :
1. Localise le dump le plus récent, valide son SHA256.
2. Lance un `postgres:16-alpine` éphémère.
3. `pg_restore` le dump dedans.
4. Compare `COUNT(*)` pour chaque table clé avec les `row_counts` du manifest.
5. Si tout matche → update `backup_history.status='verified'` + `verified_at=now()`.
6. Kill le container (trap EXIT).

## Disk monitor

```bash
./scripts/backup/disk-monitor.sh
```

Retourne un JSON des stats disque ; alerte `logger -p daemon.alert` si `used% > 85%`.

## Installation du cron (à faire une fois par Tristan en root)

```bash
sudo cp deploy/horizon-backup.cron /etc/cron.d/horizon-backup
sudo chown root:root /etc/cron.d/horizon-backup
sudo chmod 644 /etc/cron.d/horizon-backup
sudo touch /var/log/horizon-backup.log /var/log/horizon-verify.log /var/log/horizon-disk.log
sudo chown root:root /var/log/horizon-{backup,verify,disk}.log
sudo service cron reload   # ou : systemctl reload cron
```

Fréquences :
- Backup DB : quotidien à 2h00 local.
- Verify-restore : dimanche 4h00.
- Disk monitor : toutes les heures.

**Prérequis pour les mails d'alerte** : `MAILTO=tdufr01@gmail.com` dans le cron suppose qu'un MTA
(postfix, msmtp, exim) est configuré sur l'hôte. À valider séparément.

## Table `backup_history` — schéma de référence

Colonnes utiles pour l'admin (endpoint `GET /api/admin/backups`) :
- `id` (uuid) — clé technique.
- `started_at`, `completed_at` — bornes d'exécution.
- `status` — `running | success | failed | verified`.
- `file_path` — chemin absolu sur l'hôte.
- `size_bytes`, `sha256`, `row_counts_json` — invariants du dump.
- `error_message` — message d'erreur en cas de `failed`.
- `verified_at` — timestamp du dernier round-trip réussi.

## Exit codes `backup-db.sh`

- `0` — OK.
- `1` — pg_dump failed ou pré-check container KO.
- `2` — SHA256 write/format invalide.
- `3` — insert/update `backup_history` impossible.
