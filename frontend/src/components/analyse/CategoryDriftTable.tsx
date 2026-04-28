/**
 * CategoryDriftTable — dérive de chaque catégorie (mois courant vs moyenne 3 mois).
 *
 * Ligne "alert" : bg-rose-50. Max 15 visibles + bouton "Voir tout".
 */
import { memo, useMemo, useState } from "react";

import { useCategoryDrift } from "@/api/analysis";
import { CategoryDriftDetailModal } from "@/components/analyse/CategoryDriftDetailModal";
import { formatCents } from "@/lib/forecastFormat";

interface Props {
  entityId?: number;
  seuilPct?: number;
}

function formatPct(v: number): string {
  if (!Number.isFinite(v)) return "—";
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(1)} %`;
}

function formatDeltaEuros(cents: number): string {
  const sign = cents > 0 ? "+" : cents < 0 ? "−" : "";
  return `${sign}${formatCents(Math.abs(cents))}`;
}

function Skeleton() {
  return (
    <div className="space-y-2">
      <div className="h-8 animate-pulse rounded bg-slate-100" />
      <div className="h-8 animate-pulse rounded bg-slate-100" />
      <div className="h-8 animate-pulse rounded bg-slate-100" />
      <div className="h-8 animate-pulse rounded bg-slate-100" />
      <div className="h-8 animate-pulse rounded bg-slate-100" />
    </div>
  );
}

function CategoryDriftTableInner({ entityId, seuilPct = 20 }: Props) {
  const [showAll, setShowAll] = useState(false);
  const [drilledCategoryId, setDrilledCategoryId] = useState<number | null>(null);
  const query = useCategoryDrift({ entityId, seuilPct });

  const rows = query.data?.rows ?? [];
  const threshold = query.data?.seuil_pct ?? seuilPct;
  const alertCount = useMemo(
    () => rows.filter((r) => r.status === "alert").length,
    [rows],
  );
  const visible = useMemo(
    () => (showAll ? rows : rows.slice(0, 15)),
    [rows, showAll],
  );

  return (
    <div className="rounded-xl border border-line-soft bg-panel p-5 shadow-card">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="text-[15px] font-semibold text-ink">
            Dérives par catégorie
          </div>
          <div className="mt-0.5 text-[12.5px] text-muted-foreground">
            Mois en cours vs moyenne des 3 mois précédents · seuil ±{threshold} %
            · cliquez une ligne pour voir les transactions concernées
          </div>
        </div>
        {alertCount > 0 && (
          <span className="inline-flex items-center rounded-full bg-rose-50 px-2.5 py-1 text-[11.5px] font-medium text-rose-900">
            {alertCount} dérive{alertCount > 1 ? "s" : ""} au-delà du seuil
          </span>
        )}
      </div>

      {query.isLoading ? (
        <Skeleton />
      ) : query.isError ? (
        <div
          role="alert"
          className="rounded-md bg-rose-50 px-3 py-2 text-[12.5px] text-rose-900"
        >
          Impossible de charger les dérives.
        </div>
      ) : rows.length === 0 ? (
        <div className="flex h-[140px] items-center justify-center text-[13px] text-muted-foreground">
          Aucune donnée sur la période analysée.
        </div>
      ) : (
        <>
          <div className="overflow-hidden rounded-lg border border-line-soft">
            <table className="w-full text-[13px]">
              <thead>
                <tr className="border-b border-line-soft bg-panel-2 text-left">
                  <th className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Catégorie
                  </th>
                  <th className="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Mois courant
                  </th>
                  <th className="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Moyenne 3 m
                  </th>
                  <th className="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Écart €
                  </th>
                  <th className="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Écart %
                  </th>
                  <th className="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Statut
                  </th>
                </tr>
              </thead>
              <tbody>
                {visible.map((r) => (
                  <tr
                    key={r.category_id}
                    onClick={() => setDrilledCategoryId(r.category_id)}
                    className={
                      "cursor-pointer border-b border-line-soft last:border-0 hover:bg-panel-2/60 " +
                      (r.status === "alert" ? "bg-rose-50 hover:bg-rose-100/50" : "")
                    }
                  >
                    <td
                      className={
                        "px-3 py-2 " +
                        (r.status === "alert" ? "text-rose-900" : "text-ink")
                      }
                    >
                      {r.label}
                    </td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums text-ink-2">
                      {formatCents(r.current_cents)}
                    </td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums text-ink-2">
                      {formatCents(r.avg3m_cents)}
                    </td>
                    <td
                      className={
                        "px-3 py-2 text-right font-mono tabular-nums " +
                        (r.status === "alert"
                          ? "text-rose-900"
                          : r.delta_cents >= 0
                            ? "text-ink"
                            : "text-ink-2")
                      }
                    >
                      {formatDeltaEuros(r.delta_cents)}
                    </td>
                    <td
                      className={
                        "px-3 py-2 text-right font-mono tabular-nums " +
                        (r.status === "alert" ? "text-rose-900" : "text-ink-2")
                      }
                    >
                      {formatPct(r.delta_pct)}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {r.status === "alert" ? (
                        <span className="inline-flex items-center rounded-full bg-rose-100 px-2 py-0.5 text-[11px] font-medium text-rose-900">
                          Dérive
                        </span>
                      ) : (
                        <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600">
                          Normal
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {rows.length > 15 && (
            <div className="mt-3 flex justify-end">
              <button
                type="button"
                onClick={() => setShowAll((v) => !v)}
                className="rounded-sm border border-line-soft bg-panel px-3 py-1 text-[12px] font-medium text-ink-2 hover:bg-panel-2"
              >
                {showAll
                  ? "Réduire"
                  : `Voir tout (${rows.length - 15} de plus)`}
              </button>
            </div>
          )}
        </>
      )}

      <CategoryDriftDetailModal
        open={drilledCategoryId !== null}
        categoryId={drilledCategoryId}
        entityId={entityId}
        onClose={() => setDrilledCategoryId(null)}
      />
    </div>
  );
}

export const CategoryDriftTable = memo(CategoryDriftTableInner);
