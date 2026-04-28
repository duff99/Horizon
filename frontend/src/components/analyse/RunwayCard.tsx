/**
 * RunwayCard — autonomie de trésorerie (Runway).
 *
 * Répond à la question « combien de mois je peux tenir si je continue
 * comme ça ? ». Lecture pédagogique : phrase synthétique en haut, chiffre
 * principal grand, ventilation détaillée en dessous, projection 6 mois.
 */
import { memo, useMemo } from "react";
import { Line, LineChart, ResponsiveContainer } from "recharts";

import { useRunway } from "@/api/analysis";
import { formatCents } from "@/lib/forecastFormat";
import { cn } from "@/lib/utils";

interface Props {
  entityId?: number;
}

function ringClass(status: string): string {
  switch (status) {
    case "critical":
      return "ring-2 ring-rose-400";
    case "warning":
      return "ring-1 ring-rose-200";
    default:
      return "";
  }
}

interface StatusInfo {
  label: string;
  className: string;
  /** Phrase pédagogique d'interprétation. */
  interpretation: (months: number | null) => string;
}

function statusInfo(status: string): StatusInfo {
  switch (status) {
    case "critical":
      return {
        label: "Critique",
        className: "bg-rose-50 text-rose-900",
        interpretation: (m) =>
          `Moins de 6 mois de trésorerie devant vous (${m ?? "?"} mois). À ce rythme, vous serez à court avant ${m ?? "?"} mois. Action recommandée : rentrer du cash (factures impayées) ou réduire les sorties.`,
      };
    case "warning":
      return {
        label: "Vigilance",
        className: "bg-amber-50 text-amber-900",
        interpretation: (m) =>
          `Entre 6 et 12 mois de trésorerie devant vous (${m ?? "?"} mois). Confortable mais à surveiller — un imprévu peut faire basculer en zone critique.`,
      };
    case "ok":
      return {
        label: "Stable",
        className: "bg-emerald-50 text-emerald-900",
        interpretation: (m) =>
          m == null
            ? "Vos entrées couvrent vos sorties — vous ne consommez pas votre trésorerie."
            : `Plus de 12 mois de trésorerie devant vous (${m} mois). Situation saine, vous pouvez investir.`,
      };
    default:
      return {
        label: "N/A",
        className: "bg-slate-100 text-slate-600",
        interpretation: () =>
          "Pas assez d'historique pour calculer (besoin de 3 mois de transactions au moins).",
      };
  }
}

function Skeleton() {
  return (
    <div>
      <div className="h-3 w-48 animate-pulse rounded bg-slate-100" />
      <div className="mt-3 h-14 w-40 animate-pulse rounded bg-slate-100" />
      <div className="mt-4 h-3 w-48 animate-pulse rounded bg-slate-100" />
      <div className="mt-2 h-3 w-48 animate-pulse rounded bg-slate-100" />
      <div className="mt-4 h-12 animate-pulse rounded bg-slate-100" />
    </div>
  );
}

function RunwayCardInner({ entityId }: Props) {
  const query = useRunway({ entityId });
  const data = query.data;

  const sparklineData = useMemo(
    () => (data?.forecast_balance_6m_cents ?? []).map((v, i) => ({ i, v })),
    [data?.forecast_balance_6m_cents],
  );
  const burnNegative = (data?.burn_rate_cents ?? 0) < 0;

  const runwayDisplay =
    data?.runway_months == null
      ? "∞"
      : data.runway_months >= 24
        ? "24+"
        : String(data.runway_months);

  const status = data?.status ?? "none";
  const info = statusInfo(status);

  return (
    <div
      className={cn(
        "rounded-xl border border-line-soft bg-panel p-5 shadow-card",
        ringClass(status),
      )}
    >
      <div className="mb-3 flex items-start justify-between gap-2">
        <div>
          <div className="text-[15px] font-semibold text-ink">
            Autonomie de trésorerie{" "}
            <span className="text-[12px] font-normal text-muted-foreground">
              (Runway)
            </span>
          </div>
          <div className="mt-0.5 text-[12.5px] text-muted-foreground">
            Combien de mois pouvez-vous tenir si vous continuez à dépenser
            au rythme actuel ?
          </div>
        </div>
        {data && (
          <span
            className={cn(
              "inline-flex shrink-0 items-center rounded-full px-2.5 py-1 text-[11.5px] font-medium",
              info.className,
            )}
          >
            {info.label}
          </span>
        )}
      </div>

      {query.isLoading || !data ? (
        <Skeleton />
      ) : query.isError ? (
        <div
          role="alert"
          className="rounded-md bg-rose-50 px-3 py-2 text-[12.5px] text-rose-900"
        >
          Impossible de calculer l'autonomie de trésorerie.
        </div>
      ) : (
        <>
          <div className="flex items-baseline gap-2">
            <div className="font-mono text-[56px] font-semibold leading-none tabular-nums text-ink">
              {runwayDisplay}
            </div>
            <div className="text-[13px] text-muted-foreground">
              {runwayDisplay === "∞" ? "trésorerie stable" : "mois"}
            </div>
          </div>

          <p className="mt-3 rounded-md bg-panel-2/50 px-3 py-2 text-[12.5px] leading-relaxed text-ink-2">
            {info.interpretation(data.runway_months)}
          </p>

          <dl className="mt-4 grid grid-cols-2 gap-3 text-[12.5px]">
            <div>
              <dt className="text-muted-foreground">
                Consommation mensuelle{" "}
                <span className="text-[11px]">(Burn rate)</span>
              </dt>
              <dd
                className={cn(
                  "mt-0.5 font-mono tabular-nums",
                  burnNegative ? "text-rose-600" : "text-emerald-600",
                )}
              >
                {burnNegative ? "−" : "+"}
                {formatCents(Math.abs(data.burn_rate_cents))}
              </dd>
              <dd className="mt-0.5 text-[11px] text-muted-foreground">
                {burnNegative
                  ? "vous consommez ce montant chaque mois en moyenne"
                  : "vos entrées dépassent vos sorties chaque mois"}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">
                Trésorerie disponible aujourd'hui
              </dt>
              <dd className="mt-0.5 font-mono tabular-nums text-ink">
                {formatCents(data.current_balance_cents)}
              </dd>
              <dd className="mt-0.5 text-[11px] text-muted-foreground">
                solde cumulé de vos comptes bancaires
              </dd>
            </div>
          </dl>

          {sparklineData.length >= 2 && (
            <div className="mt-4">
              <div className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Solde projeté sur les 6 prochains mois
              </div>
              <div style={{ width: "100%", height: 56 }}>
                <ResponsiveContainer>
                  <LineChart
                    data={sparklineData}
                    margin={{ top: 2, right: 2, bottom: 2, left: 2 }}
                  >
                    <Line
                      type="monotone"
                      dataKey="v"
                      stroke={burnNegative ? "#e11d48" : "#059669"}
                      strokeWidth={1.75}
                      dot={false}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-1 text-[11px] text-muted-foreground">
                Extrapolation à partir du burn rate moyen (sans tenir compte
                de vos engagements futurs).
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export const RunwayCard = memo(RunwayCardInner);
