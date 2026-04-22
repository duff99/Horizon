import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useMonthComparison } from "@/api/dashboardComparison";

const EUR_COMPACT = new Intl.NumberFormat("fr-FR", {
  maximumFractionDigits: 0,
});

const EUR_FULL = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 2,
});

function formatAxis(euros: number): string {
  return `${EUR_COMPACT.format(euros)} €`;
}

function formatEur(euros: number): string {
  return EUR_FULL.format(euros);
}

interface Row {
  name: string;
  current_value: number;
  previous_value: number;
}

interface Props {
  entityId: number | null;
}

export function MonthComparisonCard({ entityId }: Props) {
  const { data, isLoading, isError } = useMonthComparison(entityId);

  const rows = useMemo<Row[]>(() => {
    if (!data) return [];
    return [
      {
        name: "Encaissements",
        current_value: data.current.in_cents / 100,
        previous_value: data.previous.in_cents / 100,
      },
      {
        name: "Décaissements",
        current_value: Math.abs(data.current.out_cents) / 100,
        previous_value: Math.abs(data.previous.out_cents) / 100,
      },
    ];
  }, [data]);

  if (isLoading) {
    return (
      <div className="rounded-xl border border-line-soft bg-panel p-5 shadow-card">
        <div className="h-4 w-80 animate-pulse rounded bg-line-soft" />
        <div className="mt-3 h-3 w-64 animate-pulse rounded bg-line-soft" />
        <div className="mt-4 h-[280px] animate-pulse rounded bg-line-soft" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="rounded-xl border border-line-soft bg-panel p-5 shadow-card">
        <div className="text-[13px] font-semibold text-ink">
          Réalisé mois en cours vs mois précédent
        </div>
        <div className="mt-3 text-[12px] text-muted-foreground">
          Données indisponibles pour la comparaison mensuelle.
        </div>
      </div>
    );
  }

  const currentLabel = data.current.month_label;
  const previousLabel = data.previous.month_label;

  return (
    <div className="rounded-xl border border-line-soft bg-panel p-5 shadow-card">
      <div className="mb-4">
        <div className="text-[13px] font-semibold text-ink">
          Réalisé mois en cours vs mois précédent
        </div>
        <div className="mt-0.5 text-[12px] text-muted-foreground">
          Comparaison de {currentLabel} à {previousLabel}
        </div>
      </div>
      <div style={{ width: "100%", height: 280 }}>
        <ResponsiveContainer>
          <BarChart
            data={rows}
            margin={{ top: 8, right: 16, bottom: 8, left: 0 }}
            barGap={6}
            barCategoryGap="25%"
          >
            <defs>
              <pattern
                id="pattern-previous"
                patternUnits="userSpaceOnUse"
                width="6"
                height="6"
                patternTransform="rotate(45)"
              >
                <rect
                  width="6"
                  height="6"
                  fill="hsl(var(--accent) / 0.12)"
                />
                <line
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="6"
                  stroke="hsl(var(--accent))"
                  strokeWidth="2"
                  strokeOpacity="0.55"
                />
              </pattern>
            </defs>
            <CartesianGrid
              strokeDasharray="2 2"
              stroke="hsl(var(--line))"
              vertical={false}
            />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 12, fill: "hsl(var(--ink))" }}
              axisLine={{ stroke: "hsl(var(--line))" }}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "hsl(var(--muted-fg))" }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => formatAxis(Number(v))}
              width={72}
            />
            <Tooltip
              cursor={{ fill: "hsl(var(--line) / 0.3)" }}
              contentStyle={{
                background: "hsl(var(--panel))",
                border: "1px solid hsl(var(--line))",
                borderRadius: 8,
                fontSize: 12,
                fontVariantNumeric: "tabular-nums",
              }}
              formatter={(value, name) => [
                formatEur(Number(value)),
                String(name),
              ]}
            />
            <Legend
              wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
              iconType="square"
            />
            <Bar
              dataKey="current_value"
              fill="hsl(var(--accent))"
              name={currentLabel}
              radius={[3, 3, 0, 0]}
              maxBarSize={56}
            />
            <Bar
              dataKey="previous_value"
              fill="url(#pattern-previous)"
              stroke="hsl(var(--accent))"
              strokeOpacity={0.35}
              strokeWidth={1}
              name={previousLabel}
              radius={[3, 3, 0, 0]}
              maxBarSize={56}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
