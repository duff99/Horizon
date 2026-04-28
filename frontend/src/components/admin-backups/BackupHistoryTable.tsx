/**
 * BackupHistoryTable — tableau des 50 derniers backups, ligne expandable.
 *
 * Cliquer une ligne déplie un panneau avec les détails (row counts,
 * sha256 abrégé, file_path, error_message complet).
 */
import { Fragment, useState } from 'react';

import type { BackupHistoryRow, BackupStatus, BackupType } from '@/types/backup';

const STATUS_LABEL: Record<BackupStatus, { label: string; classes: string }> = {
  pending: { label: 'En attente', classes: 'bg-slate-100 text-slate-700 border-slate-200' },
  running: { label: 'En cours', classes: 'bg-amber-100 text-amber-900 border-amber-200' },
  success: { label: 'Réussi', classes: 'bg-emerald-100 text-emerald-900 border-emerald-200' },
  failed: { label: 'Échec', classes: 'bg-rose-100 text-rose-900 border-rose-200' },
  verified: { label: 'Vérifié', classes: 'bg-emerald-50 text-emerald-900 border-emerald-300' },
};

const TYPE_LABEL: Record<BackupType, string> = {
  scheduled: 'Automatique',
  manual: 'Manuel',
  'pre-op': 'Pré-opération',
  'restore-test': 'Test restore',
};

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('fr-FR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
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

function shortSha(sha: string | null): string {
  if (!sha) return '—';
  return `${sha.slice(0, 8)}…${sha.slice(-6)}`;
}

interface Props {
  rows: BackupHistoryRow[];
}

export function BackupHistoryTable({ rows }: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (rows.length === 0) {
    return (
      <div className="rounded-xl border border-line-soft bg-panel p-8 text-center text-[13px] text-muted-foreground shadow-card">
        Aucune sauvegarde enregistrée pour le moment.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-line-soft bg-panel shadow-card">
      <table className="w-full text-[13px]">
        <thead>
          <tr className="border-b border-line-soft bg-panel-2 text-left">
            <th className="w-8 px-2 py-2"></th>
            <th className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Date
            </th>
            <th className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Type
            </th>
            <th className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Statut
            </th>
            <th className="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              DB
            </th>
            <th className="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Imports
            </th>
            <th className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Vérifié
            </th>
            <th className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Résumé
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const isExpanded = expandedId === r.id;
            const stat = STATUS_LABEL[r.status];
            const summary =
              r.status === 'failed'
                ? `${r.errorStep ?? '?'}: ${r.errorMessage?.slice(0, 80) ?? ''}`
                : r.rowCountsJson
                  ? `${Object.values(r.rowCountsJson).reduce((a, b) => a + b, 0)} lignes`
                  : '—';

            return (
              <Fragment key={r.id}>
                <tr
                  className={
                    'cursor-pointer border-b border-line-soft last:border-0 hover:bg-panel-2'
                  }
                  onClick={() => setExpandedId(isExpanded ? null : r.id)}
                >
                  <td className="px-2 py-2 text-muted-foreground">
                    {isExpanded ? '▾' : '▸'}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-ink">
                    {formatDateTime(r.startedAt)}
                  </td>
                  <td className="px-3 py-2 text-ink-2">{TYPE_LABEL[r.type]}</td>
                  <td className="px-3 py-2">
                    <span
                      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${stat.classes}`}
                    >
                      {stat.label}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-[12.5px] tabular-nums text-ink-2">
                    {formatBytes(r.sizeBytes)}
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-[12.5px] tabular-nums text-ink-2">
                    {formatBytes(r.importsSizeBytes)}
                  </td>
                  <td className="px-3 py-2 text-[12px] text-muted-foreground">
                    {r.verifiedAt ? formatDateTime(r.verifiedAt) : '—'}
                  </td>
                  <td
                    className={`px-3 py-2 text-[12px] ${
                      r.status === 'failed' ? 'text-rose-700' : 'text-muted-foreground'
                    }`}
                  >
                    {summary.length > 80 ? summary.slice(0, 80) + '…' : summary}
                  </td>
                </tr>

                {isExpanded && (
                  <tr className="bg-panel-2/40">
                    <td colSpan={8} className="px-4 py-3 text-[12px]">
                      <div className="grid grid-cols-1 gap-x-6 gap-y-2 md:grid-cols-2">
                        {r.status === 'failed' && (
                          <div className="md:col-span-2 rounded-md border border-rose-200 bg-rose-50/40 p-3 text-rose-900">
                            <div className="font-semibold">
                              Étape qui a échoué : {r.errorStep ?? '(inconnue)'}
                            </div>
                            <pre className="mt-1.5 whitespace-pre-wrap font-mono text-[11.5px]">
                              {r.errorMessage ?? '(pas de message)'}
                            </pre>
                          </div>
                        )}

                        {r.rowCountsJson && (
                          <div>
                            <div className="font-semibold text-ink">
                              Lignes capturées
                            </div>
                            <div className="mt-1 grid grid-cols-2 gap-x-4 gap-y-0.5">
                              {Object.entries(r.rowCountsJson).map(([k, v]) => (
                                <div key={k} className="flex justify-between">
                                  <span className="text-muted-foreground">{k}</span>
                                  <span className="font-mono tabular-nums">{v}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        <div className="space-y-1.5">
                          <div>
                            <span className="font-semibold">Fichier dump : </span>
                            <span className="font-mono text-[11.5px] break-all">
                              {r.filePath}
                            </span>
                          </div>
                          {r.sha256 && (
                            <div>
                              <span className="font-semibold">SHA256 dump : </span>
                              <span className="font-mono text-[11.5px]">
                                {shortSha(r.sha256)}
                              </span>
                            </div>
                          )}
                          {r.importsSha256 && (
                            <div>
                              <span className="font-semibold">SHA256 imports : </span>
                              <span className="font-mono text-[11.5px]">
                                {shortSha(r.importsSha256)}
                              </span>
                            </div>
                          )}
                          {r.completedAt && (
                            <div>
                              <span className="font-semibold">Terminé : </span>
                              {formatDateTime(r.completedAt)}
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
