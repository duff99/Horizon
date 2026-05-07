/**
 * G1 — Graphe de solde de trésorerie quotidien sur 90 jours.
 * AreaChart Recharts avec forward-fill implicite (toutes les dates présentes
 * car _compute_balance_trend couvre chaque jour).
 */
import { useMemo } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useDailyBalance } from "@/api/treasury";

// ---------------------------------------------------------------------------
// Formatters
// ---------------------------------------------------------------------------

const EUR = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});

const DATE_SHORT = new Intl.DateTimeFormat("fr-FR", {
  day: "2-digit",
  month: "short",
});

function formatEUR(v: number): string {
  return Number.isFinite(v) ? EUR.format(v) : "—";
}

function parseDate(s: string): Date {
  // "YYYY-MM-DD" → new Date() sans problème de timezone si on parse manuellement
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
}

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

function Skeleton() {
  return (
    <div className="rounded-xl border border-line-soft bg-panel p-4 shadow-card">
      <div className="mb-3 h-4 w-48 animate-pulse rounded bg-line-soft" />
      <div className="h-[220px] w-full animate-pulse rounded bg-line-soft" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Composant principal
// ---------------------------------------------------------------------------

interface Props {
  entityId: number;
  days?: number;
}

export function DailyBalanceChart({ entityId, days = 90 }: Props) {
  const { data, isLoading } = useDailyBalance({ entityId, days });

  const { chartData, isPositive } = useMemo(() => {
    if (!data || data.points.length === 0)
      return { chartData: [], isPositive: true };
    const lastBalance = Number(data.points[data.points.length - 1].balance);
    return {
      chartData: data.points.map((p) => ({
        date: p.date,
        dateLabel: DATE_SHORT.format(parseDate(p.date)),
        Solde: Number(p.balance),
      })),
      isPositive: lastBalance >= 0,
    };
  }, [data]);

  if (isLoading) return <Skeleton />;

  const fillColor = isPositive ? "#dcfce7" : "#fee2e2";
  const strokeColor = isPositive ? "#16a34a" : "#dc2626";

  return (
    <div className="rounded-xl border border-line-soft bg-panel p-4 shadow-card">
      <div className="mb-3 flex items-baseline justify-between">
        <div className="flex items-center gap-1.5 text-[13px] font-semibold text-ink">
          Solde de trésorerie — {days} derniers jours
          <span
            className="cursor-help text-[11px] font-normal text-muted-foreground"
            title="Solde de trésorerie reconstruit jour par jour sur 90 jours a partir du dernier releve importe."
          >
            ?
          </span>
        </div>
        {data?.latest_date && (
          <div className="text-[11px] text-muted-foreground">
            au {DATE_SHORT.format(parseDate(data.latest_date))}
          </div>
        )}
      </div>

      {chartData.length === 0 ? (
        <div className="flex h-[220px] items-center justify-center rounded-md border border-dashed border-line-soft text-[13px] text-muted-foreground">
          Aucun import disponible pour calculer l&apos;historique de solde.
        </div>
      ) : (
        <div style={{ width: "100%", height: 220 }}>
          <ResponsiveContainer>
            <AreaChart
              data={chartData}
              margin={{ top: 8, right: 16, bottom: 8, left: 0 }}
            >
              <defs>
                <linearGradient id="daily-balance-grad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={fillColor} stopOpacity={0.8} />
                  <stop offset="100%" stopColor={fillColor} stopOpacity={0.1} />
                </linearGradient>
              </defs>
              <CartesianGrid
                strokeDasharray="2 2"
                stroke="hsl(var(--line))"
                vertical={false}
              />
              <XAxis
                dataKey="dateLabel"
                tick={{ fontSize: 11, fill: "hsl(var(--muted-fg))" }}
                axisLine={{ stroke: "hsl(var(--line))" }}
                tickLine={false}
                interval="preserveStartEnd"
                minTickGap={24}
              />
              <YAxis
                tick={{ fontSize: 11, fill: "hsl(var(--muted-fg))" }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v: number) => formatEUR(v)}
                width={90}
              />
              <Tooltip
                contentStyle={{
                  background: "hsl(var(--panel))",
                  border: "1px solid hsl(var(--line))",
                  borderRadius: 8,
                  fontSize: 12,
                }}
                formatter={(v) => [formatEUR(Number(v)), "Solde"]}
                labelFormatter={(label) => String(label)}
              />
              <ReferenceLine y={0} stroke="#94a3b8" strokeDasharray="4 2" />
              <Area
                type="monotone"
                dataKey="Solde"
                stroke={strokeColor}
                strokeWidth={2}
                fill="url(#daily-balance-grad)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
