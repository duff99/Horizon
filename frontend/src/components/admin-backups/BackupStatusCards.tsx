/**
 * BackupStatusCards — 4 cartes synthèse en haut de la page Sauvegardes.
 *
 * 1. Dernier backup réussi (success/verified) → âge + taille DB+imports
 * 2. Dernier verify-restore réussi → âge
 * 3. Dernier échec (s'il y en a un) → étape + message tronqué
 * 4. Espace disque sur la partition / → used_pct + GB libres
 */
import type {
  BackupDiskStats,
  BackupHistoryRow,
} from '@/types/backup';

function formatRelative(iso: string | null): string {
  if (!iso) return 'Jamais';
  const ms = Date.now() - new Date(iso).getTime();
  if (ms < 0) return "À l'instant";
  const min = Math.floor(ms / 60_000);
  if (min < 1) return "À l'instant";
  if (min < 60) return `il y a ${min} min`;
  const hours = Math.floor(min / 60);
  if (hours < 24) return `il y a ${hours} h`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `il y a ${days} j`;
  return new Date(iso).toLocaleDateString('fr-FR');
}

function formatBytes(bytes: number | null): string {
  if (!bytes) return '—';
  const units = ['o', 'Ko', 'Mo', 'Go', 'To'];
  let v = bytes;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(v >= 100 ? 0 : 1)} ${units[i]}`;
}

interface Props {
  rows: BackupHistoryRow[];
  disk: BackupDiskStats | undefined;
}

export function BackupStatusCards({ rows, disk }: Props) {
  const lastSuccess = rows.find(
    (r) => r.status === 'success' || r.status === 'verified'
  );
  const lastVerify = rows.find((r) => r.verifiedAt !== null);
  const lastFailure = rows.find((r) => r.status === 'failed');

  const successAgeHours = lastSuccess
    ? (Date.now() - new Date(lastSuccess.startedAt).getTime()) / 3_600_000
    : null;
  const successTooOld = successAgeHours === null || successAgeHours > 26;

  const verifyAgeDays = lastVerify?.verifiedAt
    ? (Date.now() - new Date(lastVerify.verifiedAt).getTime()) / 86_400_000
    : null;
  const verifyTooOld = verifyAgeDays === null || verifyAgeDays > 8;

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
      <Card
        title="Dernier backup réussi"
        accent={successTooOld ? 'danger' : 'ok'}
        primary={lastSuccess ? formatRelative(lastSuccess.startedAt) : 'Aucun'}
        secondary={
          lastSuccess
            ? `DB ${formatBytes(lastSuccess.sizeBytes)} · Imports ${formatBytes(lastSuccess.importsSizeBytes)}`
            : 'Pas encore de backup réussi'
        }
      />
      <Card
        title="Dernier verify-restore"
        accent={verifyTooOld ? 'warning' : 'ok'}
        primary={
          lastVerify?.verifiedAt
            ? formatRelative(lastVerify.verifiedAt)
            : 'Jamais'
        }
        secondary={
          verifyTooOld
            ? 'Test de restauration trop ancien (> 8 j)'
            : 'Restauration testée OK'
        }
      />
      <Card
        title="Dernier échec"
        accent={lastFailure ? 'danger' : 'neutral'}
        primary={lastFailure ? formatRelative(lastFailure.startedAt) : 'Aucun'}
        secondary={
          lastFailure
            ? `${lastFailure.errorStep ?? '?'} · ${
                lastFailure.errorMessage?.slice(0, 60) ?? '(sans message)'
              }`
            : 'Aucun échec récent'
        }
      />
      <Card
        title="Espace disque"
        accent={
          disk?.status === 'alert'
            ? 'danger'
            : disk && disk.usedPct >= disk.thresholdPct - 10
              ? 'warning'
              : 'ok'
        }
        primary={disk ? `${disk.usedPct} %` : '—'}
        secondary={
          disk
            ? `${disk.availGb} Go libres / ${disk.sizeGb} Go (seuil ${disk.thresholdPct} %)`
            : 'Stats indisponibles'
        }
      />
    </div>
  );
}

interface CardProps {
  title: string;
  accent: 'ok' | 'warning' | 'danger' | 'neutral';
  primary: string;
  secondary: string;
}

function Card({ title, accent, primary, secondary }: CardProps) {
  const accentClass =
    accent === 'danger'
      ? 'border-rose-200 bg-rose-50/30'
      : accent === 'warning'
        ? 'border-amber-200 bg-amber-50/30'
        : accent === 'ok'
          ? 'border-emerald-200 bg-emerald-50/30'
          : 'border-line-soft bg-panel';

  return (
    <div
      className={`rounded-xl border p-4 shadow-card ${accentClass}`}
    >
      <div className="text-[11.5px] font-medium uppercase tracking-wider text-muted-foreground">
        {title}
      </div>
      <div className="mt-1.5 text-[18px] font-semibold text-ink">
        {primary}
      </div>
      <div className="mt-1 text-[12px] text-muted-foreground">
        {secondary}
      </div>
    </div>
  );
}
