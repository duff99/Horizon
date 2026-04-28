/**
 * TopMoversCard — 2 colonnes (hausses / baisses) avec sparkline 3 mois.
 */
import { memo } from "react";
import { Line, LineChart, ResponsiveContainer } from "recharts";

import { useTopMovers } from "@/api/analysis";
import { formatCents } from "@/lib/forecastFormat";
import type { TopMoverRow } from "../../types/analysis";

interface Props {
  entityId?: number;
  limit?: number;
}

function Sparkline({ values, positive }: { values: number[]; positive: boolean }) {
  const data = values.map((v, i) => ({ i, v }));
  if (data.length < 2) {
    return <div className="h-8 w-[80px]" />;
  }
  const stroke = positive ? "#059669" /* emerald-600 */ : "#e11d48"; /* rose-600 */
  return (
    <div style={{ width: 80, height: 32 }}>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
          <Line
            type="monotone"
            dataKey="v"
            stroke={stroke}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function formatDelta(cents: number): string {
  const sign = cents > 0 ? "+" : cents < 0 ? "−" : "";
  return `${sign}${formatCents(Math.abs(cents))}`;
}

function MoverRow({
  row,
  positive,
}: {
  row: TopMoverRow;
  positive: boolean;
}) {
  return (
    <li
      className="flex items-start justify-between gap-3 border-b border-line-soft py-2.5 last:border-0"
      title={row.label}
    >
      <div className="min-w-0 flex-1">
        <div className="text-[13px] leading-snug text-ink break-words">
          {row.label}
        </div>
        <div className="mt-0.5 text-[11px] text-muted-foreground">
          {row.direction === "in" ? "Entrée" : "Sortie"}
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-3 pt-0.5">
        <Sparkline values={row.sparkline_3m_cents} positive={positive} />
        <div
          className={
            "w-[96px] text-right font-mono text-[13px] tabular-nums " +
            (positive ? "text-emerald-600" : "text-rose-600")
          }
        >
          {formatDelta(row.delta_cents)}
        </div>
      </div>
    </li>
  );
}

function Skeleton() {
  return (
    <div className="space-y-2">
      <div className="h-10 animate-pulse rounded bg-slate-100" />
      <div className="h-10 animate-pulse rounded bg-slate-100" />
      <div className="h-10 animate-pulse rounded bg-slate-100" />
    </div>
  );
}

function TopMoversCardInner({ entityId, limit = 5 }: Props) {
  const query = useTopMovers({ entityId, limit });
  const increases = query.data?.increases ?? [];
  const decreases = query.data?.decreases ?? [];

  return (
    <div className="rounded-xl border border-line-soft bg-panel p-5 shadow-card">
      <div className="mb-4">
        <div className="text-[15px] font-semibold text-ink">Top mouvements</div>
        <div className="mt-0.5 text-[12.5px] text-muted-foreground">
          Variations les plus fortes vs mois précédent
        </div>
      </div>

      {query.isLoading ? (
        <Skeleton />
      ) : query.isError ? (
        <div
          role="alert"
          className="rounded-md bg-rose-50 px-3 py-2 text-[12.5px] text-rose-900"
        >
          Impossible de charger les mouvements.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
          <div>
            <div className="mb-1.5 text-[12px] font-semibold uppercase tracking-wider text-emerald-700">
              Plus fortes hausses
            </div>
            {increases.length === 0 ? (
              <div className="py-3 text-[12.5px] text-muted-foreground">
                Aucune hausse notable.
              </div>
            ) : (
              <ul>
                {increases.map((r) => (
                  <MoverRow key={r.category_id} row={r} positive={true} />
                ))}
              </ul>
            )}
          </div>
          <div>
            <div className="mb-1.5 text-[12px] font-semibold uppercase tracking-wider text-rose-700">
              Plus fortes baisses
            </div>
            {decreases.length === 0 ? (
              <div className="py-3 text-[12.5px] text-muted-foreground">
                Aucune baisse notable.
              </div>
            ) : (
              <ul>
                {decreases.map((r) => (
                  <MoverRow key={r.category_id} row={r} positive={false} />
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export const TopMoversCard = memo(TopMoversCardInner);
