/**
 * Page /administration/audit — Journal d'audit.
 *
 * Lecture seule. Réservée admin. Liste paginée des mutations (create/update/
 * delete) tracées par `app.services.audit`. Clic sur une ligne -> drawer avec
 * before_json / after_json / diff_json en JSON pretty-printed mono.
 *
 * Design choices (design-taste-frontend skill) :
 * - VISUAL_DENSITY = 7 (cockpit) : divide-y plutôt qu'un carré par ligne.
 * - Pas de card padding géant, mono pour les IDs et JSON (tokens `font-mono`).
 * - Badges d'action calmes, pas de glow/neon.
 * - Empty/loading/error states explicites.
 */
import { useQuery } from '@tanstack/react-query';
import { useMemo, useState } from 'react';

import { listAuditLog } from '@/api/auditLog';
import { listUsers } from '@/api/users';
import {
  computeRange,
  type PeriodValue,
} from '@/components/PeriodSelector';
import { cn } from '@/lib/utils';
import type { AuditAction, AuditLogEntry } from '@/types/auditLog';

// Entités traçables (cohérent avec les instrumentations backend)
const ENTITY_TYPES = [
  'User',
  'Entity',
  'BankAccount',
  'Transaction',
  'Commitment',
  'Counterparty',
  'CategorizationRule',
  'ForecastLine',
  'ForecastScenario',
] as const;

const ACTIONS: readonly AuditAction[] = ['create', 'update', 'delete'];

const PAGE_SIZE = 50;

function formatDateTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString('fr-FR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return iso;
  }
}

function actionBadgeClass(action: AuditAction): string {
  // Palette neutre, pas de glow
  if (action === 'create') {
    return 'bg-accent-soft text-accent-soft-fg border border-accent/20';
  }
  if (action === 'delete') {
    return 'bg-debit/10 text-debit border border-debit/20';
  }
  return 'bg-slate-100 text-slate-700 border border-slate-200';
}

function truncate(s: string, n = 80): string {
  if (s.length <= n) return s;
  return s.slice(0, n - 1) + '…';
}

function summarizeDiff(
  diff: Record<string, { before: unknown; after: unknown }> | null
): string {
  if (!diff) return '—';
  const keys = Object.keys(diff);
  if (keys.length === 0) return '—';
  const parts = keys.slice(0, 2).map((k) => {
    const { before, after } = diff[k];
    return `${k}: ${JSON.stringify(before)} → ${JSON.stringify(after)}`;
  });
  const suffix = keys.length > 2 ? ` (+${keys.length - 2})` : '';
  return truncate(parts.join(' · ') + suffix, 120);
}

function JsonBlock({ value }: { value: unknown }) {
  if (value == null) {
    return <p className="text-[12px] italic text-slate-400">null</p>;
  }
  return (
    <pre className="max-h-96 overflow-auto rounded-md border border-line-soft bg-slate-50 p-3 text-[11.5px] font-mono leading-relaxed text-slate-800">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

function AuditDetailDrawer({
  row,
  onClose,
}: {
  row: AuditLogEntry;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-40 flex"
      aria-modal="true"
      role="dialog"
    >
      <div
        className="flex-1 bg-slate-900/40"
        onClick={onClose}
        aria-hidden
      />
      <aside className="flex h-full w-full max-w-[680px] flex-col overflow-y-auto border-l border-line bg-panel shadow-card">
        <header className="sticky top-0 flex items-start justify-between gap-3 border-b border-line-soft bg-panel px-5 py-4">
          <div className="space-y-0.5">
            <div className="text-[11px] uppercase tracking-wider text-slate-500">
              Événement #{row.id}
            </div>
            <h2 className="text-[15px] font-semibold text-ink">
              {row.entityType}
              <span className="ml-1 font-mono text-[13px] text-slate-500">
                #{row.entityId}
              </span>
            </h2>
            <p className="text-[12px] text-slate-500">
              {formatDateTime(row.occurredAt)} —{' '}
              <span className="font-mono">
                {row.userEmail ?? 'système'}
              </span>
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100"
            aria-label="Fermer"
          >
            <svg
              viewBox="0 0 24 24"
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </header>

        <div className="flex-1 space-y-5 px-5 py-4">
          <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-[12px]">
            <dt className="text-slate-500">Action</dt>
            <dd>
              <span
                className={cn(
                  'rounded-sm px-1.5 py-0.5 text-[11px] font-medium uppercase tracking-wider',
                  actionBadgeClass(row.action),
                )}
              >
                {row.action}
              </span>
            </dd>
            <dt className="text-slate-500">Utilisateur</dt>
            <dd className="font-mono text-[12px] text-ink">
              {row.userEmail ?? '—'}{' '}
              {row.userId !== null && (
                <span className="text-slate-400">(#{row.userId})</span>
              )}
            </dd>
            <dt className="text-slate-500">IP</dt>
            <dd className="font-mono text-[12px] text-ink">
              {row.ipAddress ?? '—'}
            </dd>
            <dt className="text-slate-500">User-Agent</dt>
            <dd className="truncate font-mono text-[12px] text-ink">
              {row.userAgent ?? '—'}
            </dd>
            <dt className="text-slate-500">Request ID</dt>
            <dd className="font-mono text-[12px] text-ink">
              {row.requestId ?? '—'}
            </dd>
          </dl>

          <section>
            <h3 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Diff
            </h3>
            <JsonBlock value={row.diffJson} />
          </section>

          <section>
            <h3 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              État avant
            </h3>
            <JsonBlock value={row.beforeJson} />
          </section>

          <section>
            <h3 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              État après
            </h3>
            <JsonBlock value={row.afterJson} />
          </section>
        </div>
      </aside>
    </div>
  );
}

export function AdminAuditLogPage() {
  const [entityType, setEntityType] = useState<string>('');
  const [action, setAction] = useState<string>('');
  const [userId, setUserId] = useState<string>('');
  const [period, setPeriod] = useState<PeriodValue>(() => {
    const { from, to } = computeRange('30d');
    return { from, to, preset: '30d' };
  });
  const [offset, setOffset] = useState<number>(0);
  const [selected, setSelected] = useState<AuditLogEntry | null>(null);

  // Reset pagination quand les filtres changent
  function updateFilter(fn: () => void) {
    fn();
    setOffset(0);
  }

  const { data: users } = useQuery({
    queryKey: ['users'],
    queryFn: listUsers,
  });

  const filters = useMemo(
    () => ({
      entityType: entityType || undefined,
      action: (action as AuditAction) || undefined,
      userId: userId ? Number(userId) : undefined,
      from: period.from ? `${period.from}T00:00:00` : undefined,
      to: period.to ? `${period.to}T23:59:59` : undefined,
      limit: PAGE_SIZE,
      offset,
    }),
    [entityType, action, userId, period, offset],
  );

  const { data, isLoading, isError } = useQuery({
    queryKey: ['admin', 'audit-log', filters],
    queryFn: () => listAuditLog(filters),
  });

  const total = data?.total ?? 0;
  const items = data?.items ?? [];
  const hasMore = offset + PAGE_SIZE < total;

  return (
    <div className="mx-auto w-full max-w-[1400px] space-y-5 px-4 py-6 md:px-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight text-ink">
            Journal d'audit
          </h1>
          <p className="mt-0.5 text-[13px] text-muted-foreground">
            Trace toutes les mutations (création, modification, suppression)
            réalisées sur les données finance-sensibles. Rétention : 365 jours.
          </p>
        </div>
        <div className="text-right">
          <div className="text-[11px] uppercase tracking-wider text-slate-500">
            Total filtré
          </div>
          <div className="font-mono text-[18px] font-semibold tabular-nums text-ink">
            {total.toLocaleString('fr-FR')}
          </div>
        </div>
      </header>

      {/* Filtres — ligne horizontale, pas de carte bombée */}
      <section className="rounded-lg border border-line-soft bg-panel shadow-card">
        <div className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="flex flex-col gap-1">
            <label className="text-[11px] font-medium uppercase tracking-wider text-slate-500">
              Type d'entité
            </label>
            <select
              value={entityType}
              onChange={(e) => updateFilter(() => setEntityType(e.target.value))}
              className="h-9 rounded-md border border-line bg-panel px-2 text-[13px] text-ink focus:border-accent focus:outline-none"
            >
              <option value="">Toutes</option>
              {ENTITY_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[11px] font-medium uppercase tracking-wider text-slate-500">
              Action
            </label>
            <select
              value={action}
              onChange={(e) => updateFilter(() => setAction(e.target.value))}
              className="h-9 rounded-md border border-line bg-panel px-2 text-[13px] text-ink focus:border-accent focus:outline-none"
            >
              <option value="">Toutes</option>
              {ACTIONS.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[11px] font-medium uppercase tracking-wider text-slate-500">
              Utilisateur
            </label>
            <select
              value={userId}
              onChange={(e) => updateFilter(() => setUserId(e.target.value))}
              className="h-9 rounded-md border border-line bg-panel px-2 text-[13px] text-ink focus:border-accent focus:outline-none"
            >
              <option value="">Tous</option>
              {(users ?? []).map((u) => (
                <option key={u.id} value={u.id}>
                  {u.email}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[11px] font-medium uppercase tracking-wider text-slate-500">
              Période
            </label>
            <div className="flex items-center gap-1.5">
              <input
                type="date"
                value={period.from}
                onChange={(e) =>
                  updateFilter(() =>
                    setPeriod({ ...period, from: e.target.value, preset: 'custom' }),
                  )
                }
                className="h-9 flex-1 rounded-md border border-line bg-panel px-2 text-[13px] text-ink focus:border-accent focus:outline-none"
              />
              <span className="text-slate-400">—</span>
              <input
                type="date"
                value={period.to}
                onChange={(e) =>
                  updateFilter(() =>
                    setPeriod({ ...period, to: e.target.value, preset: 'custom' }),
                  )
                }
                className="h-9 flex-1 rounded-md border border-line bg-panel px-2 text-[13px] text-ink focus:border-accent focus:outline-none"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Table */}
      <section className="overflow-hidden rounded-lg border border-line-soft bg-panel shadow-card">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-line-soft bg-panel-2 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                <th className="px-4 py-2.5">Horodatage</th>
                <th className="px-4 py-2.5">Utilisateur</th>
                <th className="px-3 py-2.5">Action</th>
                <th className="px-4 py-2.5">Type</th>
                <th className="px-4 py-2.5">Entité</th>
                <th className="px-4 py-2.5">Changements</th>
                <th className="px-3 py-2.5 text-right">IP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line-soft">
              {isLoading && (
                <>
                  {Array.from({ length: 6 }).map((_, i) => (
                    <tr key={i}>
                      <td colSpan={7} className="px-4 py-2">
                        <div className="h-5 animate-pulse rounded bg-slate-100" />
                      </td>
                    </tr>
                  ))}
                </>
              )}
              {isError && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-[13px] text-debit">
                    Erreur lors du chargement du journal.
                  </td>
                </tr>
              )}
              {!isLoading && !isError && items.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-[13px] text-slate-500">
                    Aucune mutation sur cette période avec ces filtres.
                  </td>
                </tr>
              )}
              {items.map((row) => (
                <tr
                  key={row.id}
                  onClick={() => setSelected(row)}
                  className="cursor-pointer text-[12.5px] text-ink transition-colors hover:bg-slate-50"
                >
                  <td className="whitespace-nowrap px-4 py-2 font-mono text-[12px] text-slate-600 tabular-nums">
                    {formatDateTime(row.occurredAt)}
                  </td>
                  <td className="px-4 py-2 font-mono text-[12px] text-slate-700">
                    {row.userEmail ?? (
                      <span className="italic text-slate-400">système</span>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    <span
                      className={cn(
                        'rounded-sm px-1.5 py-0.5 text-[10.5px] font-medium uppercase tracking-wider',
                        actionBadgeClass(row.action),
                      )}
                    >
                      {row.action}
                    </span>
                  </td>
                  <td className="px-4 py-2 font-medium">{row.entityType}</td>
                  <td className="px-4 py-2 font-mono text-[12px] text-slate-600">
                    #{row.entityId}
                  </td>
                  <td className="px-4 py-2 font-mono text-[11.5px] text-slate-700">
                    {summarizeDiff(row.diffJson)}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-right font-mono text-[11.5px] text-slate-500">
                    {row.ipAddress ?? '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between border-t border-line-soft px-4 py-2.5 text-[12px] text-slate-600">
          <div>
            {total > 0 && (
              <>
                {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} sur{' '}
                {total.toLocaleString('fr-FR')}
              </>
            )}
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              className="rounded-md border border-line px-2.5 py-1 text-[12px] font-medium text-ink hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Précédent
            </button>
            <button
              type="button"
              disabled={!hasMore}
              onClick={() => setOffset(offset + PAGE_SIZE)}
              className="rounded-md border border-line px-2.5 py-1 text-[12px] font-medium text-ink hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Suivant
            </button>
          </div>
        </div>
      </section>

      {selected && (
        <AuditDetailDrawer row={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
