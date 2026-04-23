/**
 * YoYChart — ComposedChart comparant 12 mois glissants vs Y-1.
 */
import { useMemo } from "react";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useYoY } from "@/api/analysis";
import { formatMonthLabel } from "@/lib/forecastFormat";
import type { YoYPoint } from "../../types/analysis";

interface Props {
  entityId?: number;
}

interface ChartRow {
  month: string;
  monthLabel: string;
  revenues_current: number;
  revenues_previous: number;
  expenses_current: number;
  expenses_previous: number;
}

const EUR_AXIS = new Intl.NumberFormat("fr-FR", {
  maximumFractionDigits: 0,
  notation: "compact",
});

function toEuros(cents: number): number {
  return Math.round(cents / 100);
}

function Skeleton() {
  return <div className="h-[280px] animate-pulse rounded bg-slate-100" />;
}

interface TooltipPayloadItem {
  name: string;
  dataKey: string;
  value: number;
  color: string;
}

function CustomTooltip({
  active,
  payload,
  label,
  fullRow,
}: {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string;
  fullRow?: ChartRow;
}) {
  if (!active || !payload || !fullRow) return null;

  const revDelta = fullRow.revenues_current - fullRow.revenues_previous;
  const revPct =
    fullRow.revenues_previous === 0
      ? null
      : (revDelta / Math.abs(fullRow.revenues_previous)) * 100;
  const expDelta = fullRow.expenses_current - fullRow.expenses_previous;
  const expPct =
    fullRow.expenses_previous === 0
      ? null
      : (expDelta / Math.abs(fullRow.expenses_previous)) * 100;

  const fmtPct = (p: number | null) =>
    p === null ? "n/a" : `${p > 0 ? "+" : ""}${p.toFixed(1)} %`;
  const fmtDelta = (c: number) => {
    const euros = toEuros(c);
    const sign = euros > 0 ? "+" : euros < 0 ? "−" : "";
    return `${sign}${EUR_AXIS.format(Math.abs(euros))} €`;
  };

  return (
    <div className="rounded-md border border-line-soft bg-panel px-3 py-2 text-[12px] shadow-card">
      <div className="mb-1.5 font-semibold text-ink">{label}</div>
      <div className="space-y-1 tabular-nums">
        <div className="flex items-center justify-between gap-3">
          <span className="text-emerald-700">Revenus</span>
          <span className="font-mono text-emerald-700">
            {fmtDelta(revDelta)} ({fmtPct(revPct)})
          </span>
        </div>
        <div className="flex items-center justify-between gap-3">
          <span className="text-rose-700">Dépenses</span>
          <span className="font-mono text-rose-700">
            {fmtDelta(expDelta)} ({fmtPct(expPct)})
          </span>
        </div>
      </div>
    </div>
  );
}

export function YoYChart({ entityId }: Props) {
  const query = useYoY({ entityId });

  const rows = useMemo<ChartRow[]>(() => {
    const series: YoYPoint[] = query.data?.series ?? [];
    return series.map((p) => ({
      month: p.month,
      monthLabel: formatMonthLabel(p.month, "short"),
      revenues_current: toEuros(p.revenues_current),
      revenues_previous: toEuros(p.revenues_previous),
      expenses_current: toEuros(p.expenses_current),
      expenses_previous: toEuros(p.expenses_previous),
    }));
  }, [query.data]);

  const byMonth = useMemo(() => {
    const m: Record<string, ChartRow> = {};
    for (const r of rows) m[r.month] = r;
    return m;
  }, [rows]);

  return (
    <div className="rounded-xl border border-line-soft bg-panel p-5 shadow-card">
      <div className="mb-4">
        <div className="text-[15px] font-semibold text-ink">
          Comparaison année / année
        </div>
        <div className="mt-0.5 text-[12.5px] text-muted-foreground">
          Revenus et dépenses sur 12 mois glissants vs année précédente
        </div>
      </div>

      {query.isLoading ? (
        <Skeleton />
      ) : query.isError ? (
        <div
          role="alert"
          className="rounded-md bg-rose-50 px-3 py-2 text-[12.5px] text-rose-900"
        >
          Impossible de charger la comparaison Y/Y.
        </div>
      ) : rows.length === 0 ? (
        <div className="flex h-[220px] items-center justify-center text-[13px] text-muted-foreground">
          Aucune donnée sur la période.
        </div>
      ) : (
        <div style={{ width: "100%", height: 300 }}>
          <ResponsiveContainer>
            <ComposedChart
              data={rows}
              margin={{ top: 8, right: 12, bottom: 8, left: 0 }}
              barGap={2}
            >
              <CartesianGrid
                strokeDasharray="2 2"
                stroke="hsl(var(--line))"
                vertical={false}
              />
              <XAxis
                dataKey="monthLabel"
                tick={{ fontSize: 11, fill: "hsl(var(--muted-fg))" }}
                axisLine={{ stroke: "hsl(var(--line))" }}
                tickLine={false}
                interval="preserveStartEnd"
                minTickGap={16}
              />
              <YAxis
                tick={{ fontSize: 11, fill: "hsl(var(--muted-fg))" }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => `${EUR_AXIS.format(Number(v))} €`}
                width={64}
              />
              <Tooltip
                cursor={{ fill: "hsl(var(--line) / 0.25)" }}
                content={(props) => {
                  const label = props.label as string | undefined;
                  const row = label
                    ? rows.find((r) => r.monthLabel === label)
                    : undefined;
                  return (
                    <CustomTooltip
                      active={props.active}
                      payload={props.payload as unknown as TooltipPayloadItem[]}
                      label={label}
                      fullRow={row ?? (label ? byMonth[label] : undefined)}
                    />
                  );
                }}
              />
              <Legend
                wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
                iconType="square"
              />
              <Bar
                dataKey="revenues_current"
                name="Revenus (courant)"
                fill="#059669"
                radius={[2, 2, 0, 0]}
                maxBarSize={18}
              />
              <Bar
                dataKey="expenses_current"
                name="Dépenses (courant)"
                fill="#e11d48"
                radius={[2, 2, 0, 0]}
                maxBarSize={18}
              />
              <Line
                type="monotone"
                dataKey="revenues_previous"
                name="Revenus (N-1)"
                stroke="#059669"
                strokeDasharray="4 3"
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="expenses_previous"
                name="Dépenses (N-1)"
                stroke="#e11d48"
                strokeDasharray="4 3"
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
