/**
 * Page /administration/sauvegardes — supervision et déclenchement des
 * sauvegardes Horizon.
 *
 * Lecture seule sauf 2 actions admin : "Lancer un backup manuel" et
 * "Lancer un test de restore". Le déclenchement insère une row 'pending'
 * en DB ; un service systemd (horizon-backup-trigger) côté hôte la prend
 * en charge en ≤ 2 secondes et exécute le script. Le polling adaptatif
 * (3s pendant pending|running, 30s sinon) reflète l'avancement en temps
 * quasi réel.
 */
import { useState } from 'react';

import {
  useBackupDiskStats,
  useBackupHistory,
  useTriggerBackup,
} from '@/api/backups';
import { ApiError } from '@/api/client';
import { BackupAlertBanner } from '@/components/admin-backups/BackupAlertBanner';
import { BackupHistoryTable } from '@/components/admin-backups/BackupHistoryTable';
import { BackupStatusCards } from '@/components/admin-backups/BackupStatusCards';
import type { BackupTriggerType } from '@/types/backup';

export function AdminBackupsPage() {
  const historyQuery = useBackupHistory();
  const diskQuery = useBackupDiskStats();
  const trigger = useTriggerBackup();

  const [feedback, setFeedback] = useState<
    { kind: 'success' | 'error'; message: string } | null
  >(null);

  const rows = historyQuery.data ?? [];
  const inFlight = rows.find(
    (r) => r.status === 'pending' || r.status === 'running'
  );

  async function handleTrigger(type: BackupTriggerType) {
    setFeedback(null);
    try {
      await trigger.mutateAsync(type);
      setFeedback({
        kind: 'success',
        message:
          type === 'manual'
            ? 'Backup demandé. Lancement dans ≤ 2 secondes — la liste se rafraîchit toute seule.'
            : 'Test de restore demandé. Lancement dans ≤ 2 secondes.',
      });
    } catch (err) {
      const message =
        err instanceof ApiError ? err.detail : 'Erreur inconnue';
      setFeedback({ kind: 'error', message });
    }
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight text-ink">
            Sauvegardes
          </h1>
          <p className="mt-0.5 text-[13px] text-muted-foreground">
            Historique automatique, état du système, déclenchement manuel.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => historyQuery.refetch()}
            disabled={historyQuery.isFetching}
            className="rounded-md border border-line-soft bg-panel px-3 py-1.5 text-[12.5px] font-medium text-ink-2 hover:bg-panel-2 disabled:opacity-50"
          >
            {historyQuery.isFetching ? 'Actualisation…' : 'Rafraîchir'}
          </button>
          <button
            type="button"
            onClick={() => handleTrigger('restore-test')}
            disabled={trigger.isPending || !!inFlight}
            title={
              inFlight
                ? 'Une opération est déjà en cours, attends qu\'elle se termine'
                : 'Restaure le dernier backup dans un container éphémère pour vérifier qu\'il est intact'
            }
            className="rounded-md border border-accent/30 bg-accent/5 px-3 py-1.5 text-[12.5px] font-medium text-accent hover:bg-accent/10 disabled:opacity-50"
          >
            Tester un restore
          </button>
          <button
            type="button"
            onClick={() => handleTrigger('manual')}
            disabled={trigger.isPending || !!inFlight}
            title={
              inFlight
                ? 'Une opération est déjà en cours, attends qu\'elle se termine'
                : 'Crée immédiatement une sauvegarde DB + tar imports (équivalent au cron 2h)'
            }
            className="rounded-md bg-accent px-3 py-1.5 text-[12.5px] font-medium text-white hover:bg-accent/90 disabled:opacity-50"
          >
            Lancer un backup
          </button>
        </div>
      </div>

      {feedback && (
        <div
          role="status"
          className={
            feedback.kind === 'success'
              ? 'rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-[13px] text-emerald-900'
              : 'rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-[13px] text-rose-900'
          }
        >
          {feedback.message}
        </div>
      )}

      {inFlight && (
        <div
          role="status"
          className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-[13px] text-amber-900"
        >
          Opération en cours — type {inFlight.type}, statut {inFlight.status}.
          La liste se met à jour automatiquement (toutes les 3 secondes).
        </div>
      )}

      <BackupAlertBanner rows={rows} />

      <BackupStatusCards rows={rows} disk={diskQuery.data} />

      <div>
        <h2 className="mb-3 text-[15px] font-semibold text-ink">
          Historique (50 derniers)
        </h2>
        {historyQuery.isError ? (
          <div
            role="alert"
            className="rounded-md bg-rose-50 px-3 py-2 text-[13px] text-rose-900"
          >
            Impossible de charger l'historique des sauvegardes.
          </div>
        ) : historyQuery.isLoading ? (
          <div className="rounded-xl border border-line-soft bg-panel p-8 text-center text-[13px] text-muted-foreground">
            Chargement…
          </div>
        ) : (
          <BackupHistoryTable rows={rows} />
        )}
      </div>

      <details className="rounded-md border border-line-soft bg-panel/50 p-4 text-[12.5px] text-muted-foreground">
        <summary className="cursor-pointer font-medium text-ink">
          Aide &amp; dépannage
        </summary>
        <div className="mt-3 space-y-3">
          <div>
            <div className="font-semibold text-ink">Que fait un backup ?</div>
            <p>
              pg_dump de la DB Postgres en format custom (compressé) + tar du
              volume Docker des PDF importés. SHA256 + manifest JSON. Cron
              automatique tous les jours à 2h00.
            </p>
          </div>
          <div>
            <div className="font-semibold text-ink">
              Que fait un test de restore ?
            </div>
            <p>
              Restore le dernier dump dans un container Postgres éphémère, vérifie
              les row counts contre le manifest, détruit le container. Aucun impact
              sur la prod. Tourne automatiquement le dimanche à 4h.
            </p>
          </div>
          <div>
            <div className="font-semibold text-ink">
              Pourquoi le bouton est désactivé ?
            </div>
            <p>
              Une seule opération à la fois. Le service de trigger traite la
              file en série pour éviter de saturer le serveur.
            </p>
          </div>
        </div>
      </details>
    </section>
  );
}
