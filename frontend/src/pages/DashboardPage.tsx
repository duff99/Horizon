import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
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
import { fetchDashboardSummary } from "../api/dashboard";
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

function KpiCard({
  label,
  value,
  hint,
  tone = "neutral",
}: {
  label: string;
  value: string;
  hint: string;
  tone?: "neutral" | "credit" | "debit" | "warn";
}) {
  const toneClass = {
    neutral: "text-ink",
    credit: "text-credit",
    debit: "text-debit",
    warn: "text-amber-700",
  }[tone];
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
      <div className="mt-1 text-[12px] text-muted-foreground">{hint}</div>
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

export function DashboardPage() {
  const [period, setPeriod] = useState<DashboardPeriod>("current_month");
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["dashboard-summary", period],
    queryFn: () => fetchDashboardSummary({ period }),
    staleTime: 60_000,
  });

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
              hint="Crédits sur la période"
              tone="credit"
            />
            <KpiCard
              label="Sorties"
              value={formatEUR(data.outflows)}
              hint="Débits sur la période"
              tone="debit"
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

      {data && <CashflowChart summary={data} />}
    </section>
  );
}
