/**
 * AnomalyCard — transactions dépassant le p95 historique de leur catégorie (G4).
 *
 * Placement : ligne 3 de la grille AnalysePage (col-span-12),
 * après CategoryDriftTable et avant TopMoversCard.
 */
import { memo, useState } from "react";

import { useAnomalies } from "@/api/anomaly";
import { formatCents } from "@/lib/forecastFormat";

interface Props {
  entityId?: number;
}

function formatDate(iso: string): string {
  const [year, month, day] = iso.split("-");
  return `${day}/${month}/${year}`;
}

function Skeleton() {
  return (
    <div className="space-y-2">
      <div className="h-7 animate-pulse rounded bg-slate-100" />
      <div className="h-7 animate-pulse rounded bg-slate-100" />
      <div className="h-7 animate-pulse rounded bg-slate-100" />
    </div>
  );
}

const INITIAL_VISIBLE = 10;

function AnomalyCardInner({ entityId }: Props) {
  const [showAll, setShowAll] = useState(false);
  const query = useAnomalies({ entityId });

  const data = query.data;
  const rows = data?.rows ?? [];
  const visible = showAll ? rows : rows.slice(0, INITIAL_VISIBLE);

  return (
    <div className="rounded-xl border border-line-soft bg-panel p-5 shadow-card">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-1.5">
            <span className="text-[15px] font-semibold text-ink">
              Transactions inhabituelles
            </span>
            <span
              className="cursor-help text-[11px] text-muted-foreground"
              title="Une anomalie est une transaction dont le montant absolu depasse le 95e percentile historique de sa categorie sur 180 jours."
            >
              ?
            </span>
          </div>
          <div className="mt-0.5 text-[12.5px] text-muted-foreground">
            Transactions des 30 derniers jours dépassant le p95 de leur
            catégorie sur 180 jours{" "}
            {data ? `· ${data.anomaly_count} détectée${data.anomaly_count > 1 ? "s" : ""}` : ""}
          </div>
        </div>
        {(data?.anomaly_count ?? 0) > 0 && (
          <span className="inline-flex items-center rounded-full bg-rose-50 px-2.5 py-1 text-[11.5px] font-medium text-rose-900">
            {data!.anomaly_count} anomalie{data!.anomaly_count > 1 ? "s" : ""}
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
          Impossible de charger les anomalies.
        </div>
      ) : rows.length === 0 ? (
        <div className="flex h-[100px] items-center justify-center text-[13px] text-muted-foreground">
          Aucune transaction inhabituelle détectée sur les 180 derniers jours.
        </div>
      ) : (
        <>
          <div className="overflow-hidden rounded-lg border border-line-soft">
            <table className="w-full text-[13px]">
              <thead>
                <tr className="border-b border-line-soft bg-panel-2 text-left">
                  <th className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Date
                  </th>
                  <th className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Libellé
                  </th>
                  <th className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Catégorie
                  </th>
                  <th className="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Montant
                  </th>
                  <th className="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Ratio p95
                  </th>
                </tr>
              </thead>
              <tbody>
                {visible.map((r) => (
                  <tr
                    key={r.transaction_id}
                    className="border-b border-line-soft last:border-0 hover:bg-panel-2/60"
                  >
                    <td className="px-3 py-2 font-mono tabular-nums text-ink-2 text-[12px]">
                      {formatDate(r.operation_date)}
                    </td>
                    <td
                      className="max-w-[200px] truncate px-3 py-2 text-ink"
                      title={r.label}
                    >
                      {r.label}
                    </td>
                    <td className="px-3 py-2 text-ink-2">
                      {r.category_label ?? "—"}
                    </td>
                    <td
                      className="px-3 py-2 text-right font-mono tabular-nums text-rose-900"
                      title={`Seuil p95 : ${formatCents(r.p95_cents)}`}
                    >
                      {formatCents(r.amount_cents)}
                    </td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums text-rose-700">
                      ×{r.ratio.toFixed(1)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {rows.length > INITIAL_VISIBLE && (
            <div className="mt-3 flex justify-end">
              <button
                type="button"
                onClick={() => setShowAll((v) => !v)}
                className="rounded-sm border border-line-soft bg-panel px-3 py-1 text-[12px] font-medium text-ink-2 hover:bg-panel-2"
              >
                {showAll
                  ? "Réduire"
                  : `Voir les ${rows.length - INITIAL_VISIBLE} anomalie${rows.length - INITIAL_VISIBLE > 1 ? "s" : ""} restante${rows.length - INITIAL_VISIBLE > 1 ? "s" : ""}`}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export const AnomalyCard = memo(AnomalyCardInner);
