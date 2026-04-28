/**
 * BackupAlertBanner — bandeau rouge si la situation est anormale.
 *
 * Conditions :
 * - dernier backup réussi > 26h
 * - dernier verify > 8j
 * - dernier statut = failed (sur les 3 dernières opérations)
 *
 * Si aucune condition n'est remplie, le banner est invisible.
 */
import type { BackupHistoryRow } from '@/types/backup';

interface Props {
  rows: BackupHistoryRow[];
}

export function BackupAlertBanner({ rows }: Props) {
  const alerts: string[] = [];

  const lastSuccess = rows.find(
    (r) => r.status === 'success' || r.status === 'verified'
  );
  if (lastSuccess) {
    const ageH = (Date.now() - new Date(lastSuccess.startedAt).getTime()) / 3_600_000;
    if (ageH > 26) {
      alerts.push(
        `Aucun backup réussi depuis ${Math.round(ageH)} h (limite 26 h). Le cron quotidien a peut-être échoué.`
      );
    }
  } else {
    alerts.push('Aucun backup réussi enregistré.');
  }

  const lastVerify = rows.find((r) => r.verifiedAt !== null);
  if (lastVerify?.verifiedAt) {
    const ageD = (Date.now() - new Date(lastVerify.verifiedAt).getTime()) / 86_400_000;
    if (ageD > 8) {
      alerts.push(
        `Dernier test de restauration il y a ${Math.round(ageD)} j (limite 8 j). Lance un test de restore.`
      );
    }
  }

  const recentFails = rows.slice(0, 3).filter((r) => r.status === 'failed');
  if (recentFails.length > 0) {
    alerts.push(
      `${recentFails.length} échec${recentFails.length > 1 ? 's' : ''} dans les 3 dernières opérations.`
    );
  }

  if (alerts.length === 0) return null;

  return (
    <div
      role="alert"
      className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-[13px] text-rose-900"
    >
      <div className="font-semibold">⚠ Système de sauvegarde en alerte</div>
      <ul className="mt-1.5 list-disc space-y-0.5 pl-5">
        {alerts.map((a, i) => (
          <li key={i}>{a}</li>
        ))}
      </ul>
    </div>
  );
}
