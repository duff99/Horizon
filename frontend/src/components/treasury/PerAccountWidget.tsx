/**
 * G10 — Grille de cartes par compte bancaire avec solde, variation 30j
 * et mini sparkline.
 */
import { useMemo } from "react";
import { Area, AreaChart } from "recharts";
import { usePerAccount, type PerAccountBalance } from "@/api/treasury";

// ---------------------------------------------------------------------------
// Formatters
// ---------------------------------------------------------------------------

const EUR = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});

const DATE_FR = new Intl.DateTimeFormat("fr-FR", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});

function formatCents(cents: number): string {
  return EUR.format(cents / 100);
}

function parseDate(s: string): Date {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
}

// ---------------------------------------------------------------------------
// Sparkline (mini AreaChart sans axes)
// ---------------------------------------------------------------------------

function MiniSparkline({ data, positive }: { data: number[]; positive: boolean }) {
  const chartData = data.map((v, i) => ({ i, v }));
  const strokeColor = positive ? "#16a34a" : "#dc2626";
  const fillColor = positive ? "#dcfce7" : "#fee2e2";
  return (
    <AreaChart
      width={120}
      height={40}
      data={chartData}
      margin={{ top: 2, right: 0, bottom: 2, left: 0 }}
    >
      <defs>
        <linearGradient id={`spark-grad-${positive}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={fillColor} stopOpacity={0.7} />
          <stop offset="100%" stopColor={fillColor} stopOpacity={0.1} />
        </linearGradient>
      </defs>
      <Area
        type="monotone"
        dataKey="v"
        stroke={strokeColor}
        strokeWidth={1.5}
        fill={`url(#spark-grad-${positive})`}
        dot={false}
        isAnimationActive={false}
      />
    </AreaChart>
  );
}

// ---------------------------------------------------------------------------
// Carte par compte
// ---------------------------------------------------------------------------

function AccountCard({ acc }: { acc: PerAccountBalance }) {
  const isPositive = acc.balance_cents >= 0;
  const balanceClass = isPositive ? "text-credit" : "text-debit";

  const variationBadge = useMemo(() => {
    if (acc.variation_30d_cents === null || acc.variation_30d_cents === undefined)
      return null;
    const v = acc.variation_30d_cents;
    const sign = v >= 0 ? "+" : "";
    const pct =
      acc.balance_30d_ago_cents && acc.balance_30d_ago_cents !== 0
        ? ((v / Math.abs(acc.balance_30d_ago_cents)) * 100).toFixed(1)
        : null;
    const arrow = v >= 0 ? "↑" : "↓";
    const colorClass = v >= 0 ? "text-credit" : "text-debit";
    return (
      <span className={`text-[12px] font-medium ${colorClass}`}>
        {arrow} {sign}
        {formatCents(Math.abs(v))}
        {pct !== null && ` (${sign}${pct} %)`}
      </span>
    );
  }, [acc.variation_30d_cents, acc.balance_30d_ago_cents]);

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-line-soft bg-panel p-4 shadow-card">
      {/* En-tête */}
      <div>
        <div className="text-[12px] font-semibold text-ink">
          {acc.account_name}
        </div>
        <div className="text-[11px] text-muted-foreground">
          {acc.bank_name} &middot; &hellip;{acc.iban_last4}
        </div>
      </div>

      {/* Solde + sparkline */}
      <div className="flex items-end justify-between">
        <div>
          <div className={`font-mono text-[22px] font-semibold tabular-nums ${balanceClass}`}>
            {formatCents(acc.balance_cents)}
          </div>
          <div className="mt-0.5 text-[11px] text-muted-foreground">
            {variationBadge
              ? <span>30 j : {variationBadge}</span>
              : <span className="text-muted-foreground">variation n/a</span>}
          </div>
        </div>
        {acc.sparkline.length > 0 && (
          <MiniSparkline data={acc.sparkline} positive={isPositive} />
        )}
      </div>

      {/* Date dernier import */}
      {acc.last_import_date && (
        <div className="text-[10px] text-muted-foreground">
          dernier import : {DATE_FR.format(parseDate(acc.last_import_date))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

function AccountCardSkeleton() {
  return (
    <div className="rounded-xl border border-line-soft bg-panel p-4 shadow-card">
      <div className="h-3 w-32 animate-pulse rounded bg-line-soft" />
      <div className="mt-1 h-2 w-20 animate-pulse rounded bg-line-soft" />
      <div className="mt-3 h-6 w-28 animate-pulse rounded bg-line-soft" />
      <div className="mt-1 h-2 w-24 animate-pulse rounded bg-line-soft" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Widget principal
// ---------------------------------------------------------------------------

interface Props {
  entityId: number | undefined;
}

export function PerAccountWidget({ entityId }: Props) {
  const { data, isLoading } = usePerAccount({ entityId });

  if (!entityId) return null;

  return (
    <div>
      <div className="mb-3 flex items-center gap-1.5 text-[13px] font-semibold text-ink">
        Position par compte bancaire
        <span
          className="cursor-help text-[11px] font-normal text-muted-foreground"
          title="Solde par compte bancaire reconstruit a partir du dernier releve importe, avec variation sur 30 jours."
        >
          ?
        </span>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {isLoading ? (
          <>
            <AccountCardSkeleton />
            <AccountCardSkeleton />
            <AccountCardSkeleton />
          </>
        ) : !data || data.accounts.length === 0 ? (
          <div className="col-span-full rounded-md border border-dashed border-line-soft px-4 py-6 text-center text-[13px] text-muted-foreground">
            Aucun compte bancaire disponible pour cette entite.
          </div>
        ) : (
          data.accounts.map((acc) => (
            <AccountCard key={acc.account_id} acc={acc} />
          ))
        )}
      </div>
    </div>
  );
}
