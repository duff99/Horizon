import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchDashboardSummary } from "../api/dashboard";
import { useEntities } from "../api/entities";
import type { DashboardPeriod, DashboardSummary } from "../types/api";

const PERIODS: { value: DashboardPeriod; label: string }[] = [
  { value: "current_month", label: "Ce mois" },
  { value: "previous_month", label: "Mois précédent" },
  { value: "last_30d", label: "30 jours" },
  { value: "last_90d", label: "90 jours" },
];

const EUR = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 2,
});

const DATE = new Intl.DateTimeFormat("fr-FR", {
  day: "2-digit",
  month: "short",
});

function formatEUR(v: string | number): string {
  const n = typeof v === "string" ? Number(v) : v;
  return Number.isFinite(n) ? EUR.format(n) : "—";
}

function formatPct(v: number): string {
  if (!Number.isFinite(v)) return "—";
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(1)} %`;
}

function relativeDelta(current: number, previous: number): number {
  if (previous === 0) return current === 0 ? 0 : Number.POSITIVE_INFINITY;
  return ((current - previous) / Math.abs(previous)) * 100;
}

function KpiCard({
  label,
  value,
  hint,
  tone = "neutral",
  delta,
}: {
  label: string;
  value: string;
  hint: string;
  tone?: "neutral" | "credit" | "debit" | "warn";
  delta?: { pct: number; betterUp: boolean };
}) {
  const toneClass = {
    neutral: "text-ink",
    credit: "text-credit",
    debit: "text-debit",
    warn: "text-amber-700",
  }[tone];

  let deltaBadge: JSX.Element | null = null;
  if (delta) {
    const isFinite = Number.isFinite(delta.pct);
    const isUp = delta.pct > 0;
    const isGood = isUp === delta.betterUp;
    const color = !isFinite
      ? "text-muted-foreground"
      : delta.pct === 0
        ? "text-muted-foreground"
        : isGood
          ? "text-credit"
          : "text-debit";
    const arrow = !isFinite
      ? "·"
      : delta.pct === 0
        ? "="
        : isUp
          ? "↑"
          : "↓";
    deltaBadge = (
      <span className={`ml-2 text-[11px] font-medium ${color}`}>
        {arrow} {isFinite ? formatPct(delta.pct) : "n/a"}
      </span>
    );
  }

  return (
    <div className="rounded-xl border border-line-soft bg-panel p-5 shadow-card">
      <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div
        className={`mt-2 font-mono text-[24px] font-semibold tabular-nums ${toneClass}`}
      >
        {value}
      </div>
      <div className="mt-1 flex items-center text-[12px] text-muted-foreground">
        <span>{hint}</span>
        {deltaBadge}
      </div>
    </div>
  );
}

function KpiSkeleton() {
  return (
    <div className="rounded-xl border border-line-soft bg-panel p-5 shadow-card">
      <div className="h-3 w-24 animate-pulse rounded bg-line-soft" />
      <div className="mt-3 h-6 w-32 animate-pulse rounded bg-line-soft" />
      <div className="mt-2 h-3 w-20 animate-pulse rounded bg-line-soft" />
    </div>
  );
}

function CashflowChart({ summary }: { summary: DashboardSummary }) {
  const data = useMemo(
    () =>
      summary.daily.map((d) => ({
        date: d.date,
        dateLabel: DATE.format(new Date(d.date)),
        Entrées: Number(d.inflows),
        Sorties: -Number(d.outflows),
      })),
    [summary.daily],
  );

  if (data.length === 0) {
    return (
      <div className="flex h-[280px] items-center justify-center rounded-xl border border-line-soft bg-panel text-[13px] text-muted-foreground shadow-card">
        Aucune transaction sur cette période.
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-line-soft bg-panel p-4 shadow-card">
      <div className="mb-3 text-[13px] font-semibold text-ink">
        Entrées / Sorties quotidiennes
      </div>
      <div style={{ width: "100%", height: 280 }}>
        <ResponsiveContainer>
          <BarChart
            data={data}
            margin={{ top: 8, right: 16, bottom: 8, left: 0 }}
          >
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
            />
            <YAxis
              tick={{ fontSize: 11, fill: "hsl(var(--muted-fg))" }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => EUR.format(Number(v)).replace(/\u202f?€/, "")}
              width={60}
            />
            <Tooltip
              contentStyle={{
                background: "hsl(var(--panel))",
                border: "1px solid hsl(var(--line))",
                borderRadius: 8,
                fontSize: 12,
              }}
              formatter={(v) => formatEUR(Number(v))}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar dataKey="Entrées" fill="hsl(var(--credit))" radius={[3, 3, 0, 0]} />
            <Bar dataKey="Sorties" fill="hsl(var(--debit))" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function BalanceTrendChart({ summary }: { summary: DashboardSummary }) {
  const data = useMemo(
    () =>
      summary.balance_trend.map((p) => ({
        date: p.date,
        dateLabel: DATE.format(new Date(p.date)),
        Solde: Number(p.balance),
      })),
    [summary.balance_trend],
  );

  if (data.length === 0) {
    return null;
  }

  return (
    <div className="rounded-xl border border-line-soft bg-panel p-4 shadow-card">
      <div className="mb-3 flex items-baseline justify-between">
        <div className="text-[13px] font-semibold text-ink">
          Solde estimé — 90 derniers jours
        </div>
        <div className="text-[11px] text-muted-foreground">
          Reconstruit à rebours depuis le dernier solde connu
        </div>
      </div>
      <div style={{ width: "100%", height: 240 }}>
        <ResponsiveContainer>
          <AreaChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
            <defs>
              <linearGradient id="balance-grad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="hsl(var(--accent))" stopOpacity={0.28} />
                <stop offset="100%" stopColor="hsl(var(--accent))" stopOpacity={0} />
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
              tickFormatter={(v) => EUR.format(Number(v)).replace(/\u202f?€/, "")}
              width={72}
            />
            <Tooltip
              contentStyle={{
                background: "hsl(var(--panel))",
                border: "1px solid hsl(var(--line))",
                borderRadius: 8,
                fontSize: 12,
              }}
              formatter={(v) => formatEUR(Number(v))}
            />
            <Area
              type="monotone"
              dataKey="Solde"
              stroke="hsl(var(--accent))"
              strokeWidth={2}
              fill="url(#balance-grad)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function DashboardPage() {
  const [period, setPeriod] = useState<DashboardPeriod>("current_month");
  const [entityId, setEntityId] = useState<number | "all">("all");
  const { data: entities = [] } = useEntities();

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["dashboard-summary", period, entityId],
    queryFn: () =>
      fetchDashboardSummary({
        period,
        entityId: entityId === "all" ? undefined : entityId,
      }),
    staleTime: 60_000,
  });

  const deltas = useMemo(() => {
    if (!data) return null;
    const inflowsDelta = relativeDelta(Number(data.inflows), Number(data.prev_inflows));
    // Outflows sont négatifs : une baisse (delta < 0) = moins de sorties → bonne nouvelle.
    const outflowsDelta = relativeDelta(
      Math.abs(Number(data.outflows)),
      Math.abs(Number(data.prev_outflows)),
    );
    return { inflowsDelta, outflowsDelta };
  }, [data]);

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight text-ink">
            Tableau de bord
          </h1>
          <p className="mt-0.5 text-[13px] text-muted-foreground">
            {data
              ? `Période : ${data.period_label}`
              : "Vue d'ensemble de vos comptes et de votre activité."}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {entities.length > 1 && (
            <select
              aria-label="Filtrer par entité"
              value={entityId === "all" ? "" : String(entityId)}
              onChange={(e) =>
                setEntityId(e.target.value === "" ? "all" : Number(e.target.value))
              }
              className="rounded-md border border-line-soft bg-panel px-3 py-1.5 text-[12.5px] text-ink shadow-card outline-none focus:border-ink-2"
            >
              <option value="">Toutes les entités</option>
              {entities.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.name}
                </option>
              ))}
            </select>
          )}

          <div
            role="tablist"
            aria-label="Période"
            className="inline-flex rounded-md border border-line-soft bg-panel p-0.5 shadow-card"
          >
            {PERIODS.map((p) => (
              <button
                key={p.value}
                type="button"
                role="tab"
                aria-selected={period === p.value}
                onClick={() => setPeriod(p.value)}
                className={
                  "px-3 py-1.5 text-[12.5px] font-medium transition-colors rounded " +
                  (period === p.value
                    ? "bg-ink text-panel"
                    : "text-ink-2 hover:text-ink")
                }
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {isError && (
        <div
          role="alert"
          className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-[12.5px] text-red-800"
        >
          Erreur de chargement : {(error as Error).message}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {isLoading || !data ? (
          <>
            <KpiSkeleton />
            <KpiSkeleton />
            <KpiSkeleton />
            <KpiSkeleton />
          </>
        ) : (
          <>
            <KpiCard
              label="Solde total"
              value={formatEUR(data.total_balance)}
              hint={
                data.total_balance_asof
                  ? `au ${new Date(data.total_balance_asof).toLocaleDateString("fr-FR")}`
                  : "Aucun import"
              }
            />
            <KpiCard
              label="Entrées"
              value={formatEUR(data.inflows)}
              hint="vs période précédente"
              tone="credit"
              delta={
                deltas
                  ? { pct: deltas.inflowsDelta, betterUp: true }
                  : undefined
              }
            />
            <KpiCard
              label="Sorties"
              value={formatEUR(data.outflows)}
              hint="vs période précédente"
              tone="debit"
              delta={
                deltas
                  ? { pct: deltas.outflowsDelta, betterUp: false }
                  : undefined
              }
            />
            <KpiCard
              label="Non catégorisées"
              value={String(data.uncategorized_count)}
              hint="Transactions à traiter"
              tone={data.uncategorized_count > 0 ? "warn" : "neutral"}
            />
          </>
        )}
      </div>

      {data && <BalanceTrendChart summary={data} />}
      {data && <CashflowChart summary={data} />}
    </section>
  );
}
