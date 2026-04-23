/**
 * EntitiesComparisonTable — colonnes = entités, lignes = KPIs.
 *
 * Si l'API retourne ≤ 1 entité accessible, le widget se masque (`return null`).
 */
import { memo, useMemo } from "react";

import { useEntitiesComparison } from "@/api/analysis";
import { formatCents } from "@/lib/forecastFormat";
import type { EntityCompareRow } from "../../types/analysis";

interface Props {
  months?: number;
}

interface KpiRow {
  key: string;
  label: string;
  render: (e: EntityCompareRow) => React.ReactNode;
  className?: (e: EntityCompareRow) => string;
}

function formatSigned(cents: number): string {
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
    </div>
  );
}

function EntitiesComparisonTableInner({ months = 1 }: Props) {
  const query = useEntitiesComparison({ months });
  const data = query.data;

  const rows: KpiRow[] = useMemo(() => [
    {
      key: "revenues",
      label: "Revenus",
      render: (e) => formatCents(e.revenues_cents),
      className: () => "text-emerald-600",
    },
    {
      key: "expenses",
      label: "Dépenses",
      render: (e) => formatCents(e.expenses_cents),
      className: () => "text-rose-600",
    },
    {
      key: "net",
      label: "Variation nette",
      render: (e) => formatSigned(e.net_variation_cents),
      className: (e) =>
        e.net_variation_cents > 0
          ? "text-emerald-600"
          : e.net_variation_cents < 0
            ? "text-rose-600"
            : "text-ink-2",
    },
    {
      key: "balance",
      label: "Solde actuel",
      render: (e) => formatCents(e.current_balance_cents),
      className: () => "text-ink",
    },
    {
      key: "burn",
      label: "Burn rate",
      render: (e) => formatSigned(e.burn_rate_cents),
      className: (e) =>
        e.burn_rate_cents < 0 ? "text-rose-600" : "text-ink-2",
    },
    {
      key: "runway",
      label: "Runway",
      render: (e) =>
        e.runway_months == null
          ? "∞"
          : e.runway_months >= 24
            ? "24+ mois"
            : `${e.runway_months} mois`,
      className: (e) =>
        e.runway_months != null && e.runway_months < 3
          ? "text-rose-600"
          : e.runway_months != null && e.runway_months < 6
            ? "text-amber-700"
            : "text-ink-2",
    },
  ], []);

  // Si 1 seule entité accessible → ne rien rendre.
  if (data && data.entities.length <= 1 && !query.isLoading) {
    return null;
  }

  return (
    <div className="rounded-xl border border-line-soft bg-panel p-5 shadow-card">
      <div className="mb-4">
        <div className="text-[15px] font-semibold text-ink">
          Comparaison des sociétés
        </div>
        <div className="mt-0.5 text-[12.5px] text-muted-foreground">
          Indicateurs clés sur {months === 1 ? "le mois en cours" : `${months} mois`}
        </div>
      </div>

      {query.isLoading ? (
        <Skeleton />
      ) : query.isError ? (
        <div
          role="alert"
          className="rounded-md bg-rose-50 px-3 py-2 text-[12.5px] text-rose-900"
        >
          Impossible de charger la comparaison.
        </div>
      ) : !data || data.entities.length === 0 ? (
        <div className="flex h-[120px] items-center justify-center text-[13px] text-muted-foreground">
          Aucune société accessible.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-line-soft">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="border-b border-line-soft bg-panel-2">
                <th className="sticky left-0 z-[1] bg-panel-2 px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Indicateur
                </th>
                {data.entities.map((e) => (
                  <th
                    key={e.entity_id}
                    className="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-wider text-ink"
                  >
                    {e.name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={row.key}
                  className="border-b border-line-soft last:border-0"
                >
                  <td className="sticky left-0 z-[1] bg-panel px-3 py-2 text-ink-2">
                    {row.label}
                  </td>
                  {data.entities.map((e) => (
                    <td
                      key={e.entity_id}
                      className={
                        "px-3 py-2 text-right font-mono tabular-nums " +
                        (row.className ? row.className(e) : "text-ink")
                      }
                    >
                      {row.render(e)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export const EntitiesComparisonTable = memo(EntitiesComparisonTableInner);
