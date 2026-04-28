/**
 * ForecastVarianceCard — compare le réalisé au prévisionnel mois par mois.
 *
 * KPI critique du pilotage : sans feedback loop forecast → réalisé,
 * le prévisionnel dérive sans qu'on le sache. Ce widget répond à
 * "mes prévisions sont-elles fiables ?".
 *
 * État vide : si aucun forecast n'a été saisi, on affiche un call-to-action
 * vers la page Prévisionnel plutôt qu'un widget mort.
 */
import { memo } from "react";
import { Link } from "react-router-dom";

import { useForecastVariance } from "@/api/analysis";
import { formatCents } from "@/lib/forecastFormat";

interface Props {
  entityId?: number;
}

function Skeleton() {
  return (
    <div className="space-y-2">
      <div className="h-8 animate-pulse rounded bg-slate-100" />
      <div className="h-8 animate-pulse rounded bg-slate-100" />
      <div className="h-8 animate-pulse rounded bg-slate-100" />
    </div>
  );
}

function formatMonth(ym: string): string {
  // "YYYY-MM" → "MMM YYYY" en français
  const [y, m] = ym.split("-");
  const date = new Date(Number(y), Number(m) - 1, 1);
  return date.toLocaleDateString("fr-FR", { month: "short", year: "numeric" });
}

function ForecastVarianceCardInner({ entityId }: Props) {
  const query = useForecastVariance({ entityId, months: 6 });

  return (
    <div className="rounded-xl border border-line-soft bg-panel p-5 shadow-card">
      <div className="mb-4">
        <div className="text-[15px] font-semibold text-ink">
          Précision du prévisionnel
        </div>
        <div className="mt-0.5 text-[12.5px] text-muted-foreground">
          Réalisé vs prévu sur les 6 derniers mois — l'écart révèle si vos
          prévisions sont fiables.
        </div>
      </div>

      {query.isLoading ? (
        <Skeleton />
      ) : query.isError ? (
        <div
          role="alert"
          className="rounded-md bg-rose-50 px-3 py-2 text-[12.5px] text-rose-900"
        >
          Impossible de charger la précision du prévisionnel.
        </div>
      ) : !query.data?.has_forecast ? (
        <div className="rounded-md border border-dashed border-line-soft bg-panel-2/40 p-6 text-center">
          <div className="text-[13px] font-medium text-ink">
            Aucune prévision saisie sur la période.
          </div>
          <div className="mt-1 text-[12.5px] text-muted-foreground">
            Saisissez vos prévisions sur la page Prévisionnel pour activer ce
            suivi.
          </div>
          <Link
            to="/previsionnel"
            className="mt-3 inline-flex rounded-md bg-accent px-3 py-1.5 text-[12.5px] font-medium text-white hover:bg-accent/90"
          >
            Aller au Prévisionnel
          </Link>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-line-soft">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="border-b border-line-soft bg-panel-2 text-left">
                <th className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Mois
                </th>
                <th className="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Prévu
                </th>
                <th className="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Réalisé
                </th>
                <th className="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Écart
                </th>
              </tr>
            </thead>
            <tbody>
              {query.data.points.map((p) => {
                const cls =
                  p.forecasted_cents === 0
                    ? "text-muted-foreground"
                    : Math.abs(p.delta_pct) > 20
                      ? "text-rose-700 font-medium"
                      : Math.abs(p.delta_pct) > 10
                        ? "text-amber-700"
                        : "text-emerald-700";
                return (
                  <tr
                    key={p.month}
                    className="border-b border-line-soft last:border-0"
                  >
                    <td className="px-3 py-2 text-ink-2">
                      {formatMonth(p.month)}
                    </td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums text-ink-2">
                      {p.forecasted_cents === 0
                        ? "—"
                        : formatCents(p.forecasted_cents)}
                    </td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums text-ink-2">
                      {formatCents(p.actual_cents)}
                    </td>
                    <td className={`px-3 py-2 text-right font-mono tabular-nums ${cls}`}>
                      {p.forecasted_cents === 0
                        ? "—"
                        : `${p.delta_pct > 0 ? "+" : ""}${p.delta_pct.toFixed(1)} %`}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export const ForecastVarianceCard = memo(ForecastVarianceCardInner);
