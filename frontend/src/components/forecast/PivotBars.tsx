import { useMemo } from "react";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { PivotResult } from "@/types/forecast";
import { formatMonthLabel } from "@/lib/forecastFormat";

// Réexporte le type pour les consommateurs
export type { PivotResult };

const EUR = new Intl.NumberFormat("fr-FR", {
  maximumFractionDigits: 0,
  signDisplay: "auto",
});

function formatEUR(cents: number): string {
  return `${EUR.format(cents / 100)} €`;
}

export interface OverlaySeries {
  scenarioId: number;
  name: string;
  color: string;
  result: PivotResult;
}

interface Props {
  result: PivotResult;
  currentMonth: string;
  overlays?: OverlaySeries[];
}

type ChartPoint = {
  month: string;
  label: string;
  isFuture: boolean;
  realized_in: number;
  realized_out: number;
  forecast_in: number;
  forecast_out: number;
  closing_past: number | null;
  closing_future: number | null;
} & Record<string, number | string | boolean | null>;

export function PivotBars({ result, currentMonth, overlays }: Props) {
  const data = useMemo<ChartPoint[]>(() => {
    const realizedByMonth = new Map(
      result.realized_series.map((s) => [s.month, s]),
    );
    const forecastByMonth = new Map(
      result.forecast_series.map((s) => [s.month, s]),
    );

    return result.months.map((m, idx) => {
      const r = realizedByMonth.get(m);
      const f = forecastByMonth.get(m);
      const closing = result.closing_balance_projection_cents[idx] ?? 0;
      const isFuture = m > currentMonth;
      const point: ChartPoint = {
        month: m,
        label: formatMonthLabel(m),
        isFuture,
        realized_in: (r?.in_cents ?? 0) / 100,
        realized_out: (r?.out_cents ?? 0) / 100,
        forecast_in: (f?.in_cents ?? 0) / 100,
        forecast_out: (f?.out_cents ?? 0) / 100,
        closing_past: m <= currentMonth ? closing / 100 : null,
        closing_future: m >= currentMonth ? closing / 100 : null,
      };
      // Une clé par overlay : "overlay_<scenarioId>"
      for (const ov of overlays ?? []) {
        const ovIdx = ov.result.months.indexOf(m);
        point[`overlay_${ov.scenarioId}`] =
          ovIdx === -1
            ? null
            : (ov.result.closing_balance_projection_cents[ovIdx] ?? 0) / 100;
      }
      return point;
    });
  }, [result, currentMonth, overlays]);

  return (
    <div style={{ width: "100%", height: 260 }}>
      <ResponsiveContainer>
        <ComposedChart
          data={data}
          margin={{ top: 8, right: 16, bottom: 8, left: 0 }}
        >
          <defs>
            <pattern
              id="pattern-in"
              patternUnits="userSpaceOnUse"
              width="6"
              height="6"
              patternTransform="rotate(45)"
            >
              <rect width="6" height="6" fill="hsl(152 55% 92%)" />
              <line
                x1="0"
                y1="0"
                x2="0"
                y2="6"
                stroke="hsl(152 48% 42%)"
                strokeWidth="2"
              />
            </pattern>
            <pattern
              id="pattern-out"
              patternUnits="userSpaceOnUse"
              width="6"
              height="6"
              patternTransform="rotate(45)"
            >
              <rect width="6" height="6" fill="hsl(354 78% 95%)" />
              <line
                x1="0"
                y1="0"
                x2="0"
                y2="6"
                stroke="hsl(354 60% 52%)"
                strokeWidth="2"
              />
            </pattern>
          </defs>
          <CartesianGrid
            strokeDasharray="2 2"
            stroke="hsl(var(--line))"
            vertical={false}
          />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11, fill: "hsl(var(--muted-fg))" }}
            axisLine={{ stroke: "hsl(var(--line))" }}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fontSize: 11, fill: "hsl(var(--muted-fg))" }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => EUR.format(Number(v))}
            width={64}
          />
          <Tooltip
            contentStyle={{
              background: "hsl(var(--panel))",
              border: "1px solid hsl(var(--line))",
              borderRadius: 8,
              fontSize: 12,
            }}
            labelFormatter={(_l, payload) => {
              const p = payload?.[0]?.payload as ChartPoint | undefined;
              return p ? formatMonthLabel(p.month, "long") : "";
            }}
            formatter={(value, name) => {
              const cents = Math.round(Number(value) * 100);
              const baseLabels: Record<string, string> = {
                realized_in: "Entrées réalisées",
                realized_out: "Sorties réalisées",
                forecast_in: "Entrées prévues",
                forecast_out: "Sorties prévues",
                closing_past: "Solde de clôture",
                closing_future: "Solde projeté",
              };
              const key = String(name);
              if (key.startsWith("overlay_")) {
                const id = Number(key.slice("overlay_".length));
                const ov = overlays?.find((o) => o.scenarioId === id);
                return [formatEUR(cents), ov?.name ?? `Scénario ${id}`];
              }
              return [formatEUR(cents), baseLabels[key] ?? key];
            }}
          />
          <ReferenceLine y={0} stroke="hsl(var(--line))" />
          <Bar
            dataKey="realized_in"
            stackId="in"
            fill="hsl(152 48% 42%)"
            radius={[3, 3, 0, 0]}
            maxBarSize={28}
          />
          <Bar
            dataKey="forecast_in"
            stackId="in"
            fill="url(#pattern-in)"
            radius={[3, 3, 0, 0]}
            maxBarSize={28}
          />
          <Bar
            dataKey="realized_out"
            stackId="out"
            fill="hsl(354 60% 52%)"
            radius={[3, 3, 0, 0]}
            maxBarSize={28}
          />
          <Bar
            dataKey="forecast_out"
            stackId="out"
            fill="url(#pattern-out)"
            radius={[3, 3, 0, 0]}
            maxBarSize={28}
          />
          <Line
            type="monotone"
            dataKey="closing_past"
            stroke="hsl(var(--accent))"
            strokeWidth={2}
            dot={false}
            connectNulls={false}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="closing_future"
            stroke="hsl(var(--accent))"
            strokeWidth={2}
            strokeDasharray="4 3"
            dot={false}
            connectNulls={false}
            isAnimationActive={false}
          />
          {(overlays ?? []).map((ov) => (
            <Line
              key={ov.scenarioId}
              type="monotone"
              dataKey={`overlay_${ov.scenarioId}`}
              stroke={ov.color}
              strokeWidth={1.5}
              strokeDasharray="6 3"
              strokeOpacity={0.75}
              dot={false}
              connectNulls={false}
              isAnimationActive={false}
              name={ov.name}
            />
          ))}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
