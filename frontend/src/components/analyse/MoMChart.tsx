/**
 * MoMChart — ComposedChart affichant les 6 mois glissants finis (MoM).
 *
 * Barres : encaissements (vert) et décaissements (rouge).
 * Ligne : net mensuel.
 * Tooltip : montants en euros + variation mensuelle en %.
 */
import { memo, useMemo } from "react";
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

import { useMoM } from "@/api/analysis";
import { formatMonthLabel } from "@/lib/forecastFormat";
import type { MoMPoint } from "../../types/analysis";

interface Props {
  entityId?: number;
}

interface ChartRow {
  month: string;
  monthLabel: string;
  revenues: number;
  expenses: number;
  net: number;
  delta_revenues_pct: number | null;
  delta_expenses_pct: number | null;
}

const EUR_FMT = new Intl.NumberFormat("fr-FR", {
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
  value: number;
  color: string;
}

function CustomTooltip({
  active,
  payload,
  label,
  row,
}: {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string;
  row?: ChartRow;
}) {
  if (!active || !payload || !row) return null;

  const fmtEur = (v: number) => `${EUR_FMT.format(Math.abs(v))} €`;
  const fmtPct = (p: number | null) => {
    if (p === null) return "—";
    return `${p > 0 ? "+" : ""}${p.toFixed(1)} %`;
  };

  return (
    <div className="rounded-md border border-line-soft bg-panel px-3 py-2 text-[12px] shadow-card">
      <div className="mb-1.5 font-semibold text-ink">{label}</div>
      <div className="space-y-1 tabular-nums">
        <div className="flex items-center justify-between gap-3">
          <span className="text-emerald-700">Encaissements</span>
          <span className="font-mono text-emerald-700">
            {fmtEur(row.revenues)}{" "}
            <span className="text-[11px] opacity-70">
              ({fmtPct(row.delta_revenues_pct)})
            </span>
          </span>
        </div>
        <div className="flex items-center justify-between gap-3">
          <span className="text-rose-700">Décaissements</span>
          <span className="font-mono text-rose-700">
            {fmtEur(row.expenses)}{" "}
            <span className="text-[11px] opacity-70">
              ({fmtPct(row.delta_expenses_pct)})
            </span>
          </span>
        </div>
        <div className="flex items-center justify-between gap-3 border-t border-line-soft pt-1">
          <span className={row.net >= 0 ? "text-emerald-800" : "text-rose-800"}>
            Net
          </span>
          <span
            className={`font-mono font-semibold ${row.net >= 0 ? "text-emerald-800" : "text-rose-800"}`}
          >
            {row.net >= 0 ? "+" : ""}
            {EUR_FMT.format(row.net)} €
          </span>
        </div>
      </div>
    </div>
  );
}

function MoMChartInner({ entityId }: Props) {
  const query = useMoM({ entityId });

  const rows = useMemo<ChartRow[]>(() => {
    const series: MoMPoint[] = query.data?.series ?? [];
    return series.map((p) => ({
      month: p.month,
      monthLabel: formatMonthLabel(p.month, "short"),
      revenues: toEuros(p.revenues_cents),
      expenses: toEuros(p.expenses_cents),
      net: toEuros(p.net_cents),
      delta_revenues_pct: p.delta_revenues_pct,
      delta_expenses_pct: p.delta_expenses_pct,
    }));
  }, [query.data]);

  const availableMonths = query.data?.available_months ?? 0;
  const hasData = availableMonths > 0;

  return (
    <div className="rounded-xl border border-line-soft bg-panel p-5 shadow-card">
      <div className="mb-4">
        <div className="text-[15px] font-semibold text-ink">
          Tendance mensuelle{" "}
          <span className="text-[12px] font-normal text-muted-foreground">
            (MoM — 6 derniers mois complets)
          </span>
        </div>
        <div className="mt-0.5 text-[12.5px] text-muted-foreground">
          Encaissements et décaissements sur les 6 mois finis avant le dernier
          import, avec variation mensuelle en %.
          {availableMonths > 0 && availableMonths < 6 && (
            <span className="ml-1 text-amber-700">
              ({availableMonths} mois disponibles sur 6)
            </span>
          )}
        </div>
      </div>

      {query.isLoading ? (
        <Skeleton />
      ) : query.isError ? (
        <div
          role="alert"
          className="rounded-md bg-rose-50 px-3 py-2 text-[12.5px] text-rose-900"
        >
          Impossible de charger la tendance mensuelle.
        </div>
      ) : !hasData ? (
        <div className="flex h-[220px] items-center justify-center text-[13px] text-muted-foreground">
          Aucune donnée sur les 6 derniers mois. Importez vos relevés pour voir
          ce graphique.
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
              />
              <YAxis
                tick={{ fontSize: 11, fill: "hsl(var(--muted-fg))" }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => `${EUR_FMT.format(Number(v))} €`}
                width={64}
              />
              <Tooltip
                cursor={{ fill: "hsl(var(--line) / 0.25)" }}
                content={(props) => {
                  const label = props.label as string | undefined;
                  const matchedRow = label
                    ? rows.find((r) => r.monthLabel === label)
                    : undefined;
                  return (
                    <CustomTooltip
                      active={props.active}
                      payload={
                        props.payload as unknown as TooltipPayloadItem[]
                      }
                      label={label}
                      row={matchedRow}
                    />
                  );
                }}
              />
              <Legend
                wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
                iconType="square"
              />
              <Bar
                dataKey="revenues"
                name="Encaissements"
                fill="#059669"
                radius={[2, 2, 0, 0]}
                maxBarSize={24}
              />
              <Bar
                dataKey="expenses"
                name="Décaissements"
                fill="#e11d48"
                radius={[2, 2, 0, 0]}
                maxBarSize={24}
              />
              <Line
                type="monotone"
                dataKey="net"
                name="Net"
                stroke="#6366f1"
                strokeWidth={2}
                dot={{ r: 3, fill: "#6366f1" }}
                isAnimationActive={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

export const MoMChart = memo(MoMChartInner);
