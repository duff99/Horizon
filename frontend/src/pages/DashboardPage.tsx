import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  fetchAlerts,
  fetchBankBalances,
  fetchCategoryBreakdown,
  fetchDashboardSummary,
  fetchTopCounterparties,
} from "../api/dashboard";
import { useEntities } from "../api/entities";
import type {
  Alert,
  BankAccountBalance,
  CategoryBreakdown,
  DashboardPeriod,
  DashboardSummary,
  TopCounterparties,
} from "../types/api";

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

      <AlertsSection entityId={entityId === "all" ? undefined : entityId} />

      {data && <BalanceTrendChart summary={data} />}

      <BankBalancesSection entityId={entityId === "all" ? undefined : entityId} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <CategoriesSection
          period={period}
          entityId={entityId === "all" ? undefined : entityId}
        />
        <TopCounterpartiesSection
          period={period}
          entityId={entityId === "all" ? undefined : entityId}
        />
      </div>

      {data && <CashflowChart summary={data} />}
    </section>
  );
}

const ALERT_STYLES: Record<Alert["severity"], { wrap: string; icon: string }> = {
  info: {
    wrap: "border-sky-200 bg-sky-50 text-sky-900",
    icon: "text-sky-600",
  },
  warning: {
    wrap: "border-amber-200 bg-amber-50 text-amber-900",
    icon: "text-amber-600",
  },
  critical: {
    wrap: "border-red-200 bg-red-50 text-red-900",
    icon: "text-red-600",
  },
};

function AlertsSection({ entityId }: { entityId?: number }) {
  const { data = [] } = useQuery<Alert[]>({
    queryKey: ["dashboard-alerts", entityId],
    queryFn: () => fetchAlerts({ entityId }),
    staleTime: 60_000,
  });
  if (data.length === 0) return null;
  return (
    <div className="space-y-2">
      {data.map((a) => {
        const styles = ALERT_STYLES[a.severity];
        return (
          <div
            key={a.id}
            role="alert"
            className={`flex items-start gap-3 rounded-lg border px-3 py-2.5 text-[13px] ${styles.wrap}`}
          >
            <svg
              aria-hidden
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              className={`mt-0.5 h-4 w-4 shrink-0 ${styles.icon}`}
            >
              <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
            <div className="flex-1">
              <div className="font-medium">{a.title}</div>
              <div className="text-[12px] opacity-85">{a.detail}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function BankBalancesSection({ entityId }: { entityId?: number }) {
  const { data = [], isLoading } = useQuery<BankAccountBalance[]>({
    queryKey: ["dashboard-bank-balances", entityId],
    queryFn: () => fetchBankBalances({ entityId }),
    staleTime: 60_000,
  });

  if (isLoading) {
    return (
      <div className="rounded-xl border border-line-soft bg-panel p-4 shadow-card">
        <div className="h-4 w-48 animate-pulse rounded bg-line-soft" />
        <div className="mt-3 h-24 animate-pulse rounded bg-line-soft" />
      </div>
    );
  }

  if (data.length === 0) {
    return null;
  }

  return (
    <div className="rounded-xl border border-line-soft bg-panel shadow-card">
      <div className="border-b border-line-soft px-4 py-3 text-[13px] font-semibold text-ink">
        Soldes par compte
      </div>
      <table className="w-full">
        <thead>
          <tr className="border-b border-line-soft bg-panel-2">
            <th className="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Société
            </th>
            <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Compte
            </th>
            <th className="px-3 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Solde
            </th>
            <th className="px-3 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Δ vs mois-1
            </th>
            <th className="px-3 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Dernier import
            </th>
          </tr>
        </thead>
        <tbody>
          {data.map((b) => {
            const delta = b.delta_vs_prev_month != null ? Number(b.delta_vs_prev_month) : null;
            return (
              <tr key={b.bank_account_id} className="border-b border-line-soft last:border-0">
                <td className="px-4 py-3 text-[13px] text-ink">{b.entity_name}</td>
                <td className="px-3 py-3 text-[13px] text-ink-2">
                  <div className="flex flex-col">
                    <span className="font-medium text-ink">{b.account_name}</span>
                    <span className="text-[11.5px] uppercase tracking-wider text-muted-foreground">
                      {b.bank_name}
                    </span>
                  </div>
                </td>
                <td className="px-3 py-3 text-right font-mono text-[13px] tabular-nums text-ink">
                  {formatEUR(b.balance)}
                </td>
                <td className="px-3 py-3 text-right font-mono text-[12.5px] tabular-nums">
                  {delta == null ? (
                    <span className="text-muted-foreground">—</span>
                  ) : (
                    <span className={delta >= 0 ? "text-credit" : "text-debit"}>
                      {delta >= 0 ? "+" : ""}
                      {formatEUR(Math.abs(delta))}
                    </span>
                  )}
                </td>
                <td className="px-3 py-3 text-right font-mono text-[12.5px] tabular-nums text-muted-foreground">
                  {b.last_import_at
                    ? new Date(b.last_import_at).toLocaleDateString("fr-FR")
                    : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

const DONUT_COLORS = [
  "#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6", "#6b7280",
];

function DonutChart({
  title,
  items,
}: {
  title: string;
  items: CategoryBreakdown["income"];
}) {
  if (items.length === 0) {
    return (
      <div className="rounded-xl border border-line-soft bg-panel p-4 shadow-card">
        <div className="mb-3 text-[13px] font-semibold text-ink">{title}</div>
        <div className="flex h-[220px] items-center justify-center text-[13px] text-muted-foreground">
          Aucune donnée sur cette période.
        </div>
      </div>
    );
  }

  const data = items.map((it, i) => ({
    name: it.name,
    value: Number(it.amount),
    color: it.color ?? DONUT_COLORS[i % DONUT_COLORS.length],
    pct: it.pct,
  }));

  return (
    <div className="rounded-xl border border-line-soft bg-panel p-4 shadow-card">
      <div className="mb-3 text-[13px] font-semibold text-ink">{title}</div>
      <div style={{ width: "100%", height: 220 }}>
        <ResponsiveContainer>
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              innerRadius={55}
              outerRadius={85}
              paddingAngle={2}
            >
              {data.map((d, i) => (
                <Cell key={i} fill={d.color} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                background: "hsl(var(--panel))",
                border: "1px solid hsl(var(--line))",
                borderRadius: 8,
                fontSize: 12,
              }}
              formatter={(v) => formatEUR(Number(v))}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="mt-2 space-y-1">
        {data.map((d, i) => (
          <li
            key={i}
            className="flex items-center justify-between text-[12px] text-ink-2"
          >
            <span className="flex items-center gap-2">
              <span
                aria-hidden
                className="h-2.5 w-2.5 rounded-sm"
                style={{ background: d.color }}
              />
              {d.name}
            </span>
            <span className="font-mono tabular-nums">
              {formatEUR(d.value)}{" "}
              <span className="text-muted-foreground">({d.pct.toFixed(0)} %)</span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function CategoriesSection({
  period,
  entityId,
}: {
  period: DashboardPeriod;
  entityId?: number;
}) {
  const { data, isLoading } = useQuery<CategoryBreakdown>({
    queryKey: ["dashboard-categories", period, entityId],
    queryFn: () => fetchCategoryBreakdown({ period, entityId }),
    staleTime: 60_000,
  });

  if (isLoading || !data) {
    return (
      <div className="rounded-xl border border-line-soft bg-panel p-4 shadow-card">
        <div className="h-4 w-40 animate-pulse rounded bg-line-soft" />
        <div className="mt-3 h-[220px] animate-pulse rounded bg-line-soft" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <DonutChart title="Entrées par catégorie" items={data.income} />
      <DonutChart title="Sorties par catégorie" items={data.expense} />
    </div>
  );
}

function TopCounterpartiesSection({
  period,
  entityId,
}: {
  period: DashboardPeriod;
  entityId?: number;
}) {
  const { data, isLoading } = useQuery<TopCounterparties>({
    queryKey: ["dashboard-top-counterparties", period, entityId],
    queryFn: () => fetchTopCounterparties({ period, entityId }),
    staleTime: 60_000,
  });

  if (isLoading || !data) {
    return (
      <div className="rounded-xl border border-line-soft bg-panel p-4 shadow-card">
        <div className="h-4 w-40 animate-pulse rounded bg-line-soft" />
        <div className="mt-3 h-[180px] animate-pulse rounded bg-line-soft" />
      </div>
    );
  }

  const TopList = ({
    title,
    items,
    tone,
  }: {
    title: string;
    items: TopCounterparties["top_inflows"];
    tone: "credit" | "debit";
  }) => (
    <div className="rounded-xl border border-line-soft bg-panel p-4 shadow-card">
      <div className="mb-3 text-[13px] font-semibold text-ink">{title}</div>
      {items.length === 0 ? (
        <div className="flex h-[100px] items-center justify-center text-[13px] text-muted-foreground">
          Aucun mouvement sur cette période.
        </div>
      ) : (
        <ul className="space-y-2">
          {items.map((it) => (
            <li
              key={`${it.counterparty_id}-${it.name}`}
              className="flex items-center justify-between text-[13px]"
            >
              <span className="truncate text-ink">{it.name}</span>
              <span
                className={`font-mono tabular-nums ${
                  tone === "credit" ? "text-credit" : "text-debit"
                }`}
              >
                {tone === "debit" ? "−" : ""}
                {formatEUR(it.amount)}
                <span className="ml-2 text-[11px] text-muted-foreground">
                  ({it.transactions_count})
                </span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );

  return (
    <div className="space-y-4">
      <TopList title="Top encaissements" items={data.top_inflows} tone="credit" />
      <TopList title="Top décaissements" items={data.top_outflows} tone="debit" />
    </div>
  );
}
