/**
 * ClientConcentrationCard — donut top 5 clients + Autres, HHI au centre.
 */
import { memo, useMemo } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { useClientConcentration } from "@/api/analysis";
import { formatCents } from "@/lib/forecastFormat";
import { cn } from "@/lib/utils";

interface Props {
  entityId?: number;
  months?: number;
}

// Palette sobre, du plus important (slate-700) aux Autres (slate-300).
const PALETTE = [
  "#1e293b", // slate-800
  "#334155", // slate-700
  "#475569", // slate-600
  "#64748b", // slate-500
  "#94a3b8", // slate-400
  "#cbd5e1", // slate-300 → "Autres"
];

function riskStyle(level: string): {
  label: string;
  className: string;
} {
  switch (level) {
    case "low":
      return {
        label: "Risque faible",
        className: "text-emerald-700",
      };
    case "medium":
      return {
        label: "Risque modéré",
        className: "text-amber-700",
      };
    case "high":
      return {
        label: "Risque élevé",
        className: "text-rose-700",
      };
    default:
      return { label: "—", className: "text-slate-500" };
  }
}

function Skeleton() {
  return (
    <div className="flex items-center gap-4">
      <div className="h-[160px] w-[160px] animate-pulse rounded-full bg-slate-100" />
      <div className="flex-1 space-y-2">
        <div className="h-3 w-32 animate-pulse rounded bg-slate-100" />
        <div className="h-3 w-24 animate-pulse rounded bg-slate-100" />
        <div className="h-3 w-28 animate-pulse rounded bg-slate-100" />
      </div>
    </div>
  );
}

function ClientConcentrationCardInner({ entityId, months = 12 }: Props) {
  const query = useClientConcentration({ entityId, months });
  const data = query.data;

  const slices = useMemo(() => {
    if (!data) return [];
    const list = data.top5.map((s, i) => ({
      name: s.name,
      value: s.amount_cents,
      share: s.share_pct,
      color: PALETTE[i % PALETTE.length],
    }));
    if (data.others_cents > 0) {
      list.push({
        name: "Autres",
        value: data.others_cents,
        share: data.others_share_pct,
        color: PALETTE[5],
      });
    }
    return list;
  }, [data]);

  const risk = riskStyle(data?.risk_level ?? "—");

  return (
    <div className="rounded-xl border border-line-soft bg-panel p-5 shadow-card">
      <div className="mb-4">
        <div className="text-[15px] font-semibold text-ink">
          Concentration clients
        </div>
        <div className="mt-0.5 text-[12.5px] text-muted-foreground">
          Répartition du CA sur {months} mois
        </div>
      </div>

      {query.isLoading ? (
        <Skeleton />
      ) : query.isError ? (
        <div
          role="alert"
          className="rounded-md bg-rose-50 px-3 py-2 text-[12.5px] text-rose-900"
        >
          Impossible de charger la concentration clients.
        </div>
      ) : !data || slices.length === 0 ? (
        <div className="flex h-[160px] items-center justify-center text-[13px] text-muted-foreground">
          Aucun encaissement sur la période.
        </div>
      ) : (
        <div className="space-y-4">
          <div className="relative flex justify-center">
            <div style={{ width: 180, height: 180 }}>
              <ResponsiveContainer>
                <PieChart>
                  <Pie
                    data={slices}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={56}
                    outerRadius={82}
                    paddingAngle={2}
                    isAnimationActive={false}
                  >
                    {slices.map((s, i) => (
                      <Cell key={i} fill={s.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: "hsl(var(--panel))",
                      border: "1px solid hsl(var(--line))",
                      borderRadius: 8,
                      fontSize: 12,
                      fontVariantNumeric: "tabular-nums",
                    }}
                    formatter={(value) => formatCents(Number(value))}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div
              aria-hidden
              className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center"
            >
              <div className="font-mono text-[20px] font-semibold tabular-nums text-ink">
                {Math.round(data.hhi)}
              </div>
              <div
                className="text-[10.5px] font-semibold uppercase tracking-wider text-muted-foreground"
                title="Indice Herfindahl-Hirschman — mesure standard de la concentration. < 1500 = faible, > 2500 = élevée."
              >
                Indice (HHI)
              </div>
              <div className={cn("mt-0.5 text-[11.5px] font-medium", risk.className)}>
                {risk.label}
              </div>
            </div>
          </div>

          <ul className="space-y-1.5">
            {slices.map((s, i) => (
              <li
                key={i}
                className="flex items-center justify-between gap-2 text-[12.5px]"
              >
                <span className="flex min-w-0 items-center gap-2">
                  <span
                    aria-hidden
                    className="h-2.5 w-2.5 shrink-0 rounded-sm"
                    style={{ background: s.color }}
                  />
                  <span className="truncate text-ink-2">{s.name}</span>
                </span>
                <span className="shrink-0 font-mono tabular-nums text-ink-2">
                  {formatCents(s.value)}
                  <span className="ml-1.5 text-muted-foreground">
                    ({s.share.toFixed(1)} %)
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export const ClientConcentrationCard = memo(ClientConcentrationCardInner);
