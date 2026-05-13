import { useMemo } from "react";
import { Wallet, TrendingUp, TrendingDown, Clock, Building2 } from "lucide-react";
import { useWorkingCapital } from "@/api/analysis";
import { formatCents } from "@/lib/forecastFormat";
import type { PivotResult } from "@/types/forecast";
import { cn } from "@/lib/utils";

interface Props {
  entityId: number;
  pivot: PivotResult | undefined;
  currentMonth: string;
}

interface KpiCardProps {
  label: string;
  value: string;
  hint?: string;
  tooltip?: string;
  tone?: "primary" | "neutral" | "positive" | "negative";
  icon?: React.ReactNode;
}

function KpiCard({ label, value, hint, tooltip, tone = "neutral", icon }: KpiCardProps) {
  return (
    <div className="rounded-lg border border-line-soft bg-panel px-3.5 py-3 shadow-sm">
      <div className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-1.5 text-[10.5px] font-medium uppercase tracking-wider text-muted-foreground">
          {icon}
          {label}
        </span>
        {tooltip && (
          <span
            title={tooltip}
            className="cursor-help text-[10.5px] text-muted-foreground"
            aria-label={tooltip}
          >
            ?
          </span>
        )}
      </div>
      <div
        className={cn(
          "mt-1 font-mono text-[19px] font-semibold tabular-nums leading-tight",
          tone === "primary" && "text-accent",
          tone === "positive" && "text-emerald-600",
          tone === "negative" && "text-rose-500",
          tone === "neutral" && "text-ink",
        )}
      >
        {value}
      </div>
      {hint && (
        <div className="mt-0.5 text-[10.5px] text-muted-foreground">{hint}</div>
      )}
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="h-[72px] animate-pulse rounded-lg border border-line-soft bg-panel-2/40" />
  );
}

export function ForecastKpiSidebar({ entityId, pivot, currentMonth }: Props) {
  const wc = useWorkingCapital({ entityId });

  // Trésorerie au mois courant (fin du mois courant si disponible, sinon
  // dernier mois clos avant la période courante). On utilise la projection
  // de clôture déjà calculée côté backend pour rester cohérent avec le
  // tableau pivot.
  const currentBalance = useMemo<number | null>(() => {
    if (!pivot) return null;
    const idx = pivot.months.indexOf(currentMonth);
    if (idx === -1) return null;
    return pivot.closing_balance_projection_cents[idx] ?? null;
  }, [pivot, currentMonth]);

  // Projection à fin de période (dernier mois de la fenêtre)
  const finalBalance = useMemo<number | null>(() => {
    if (!pivot || pivot.months.length === 0) return null;
    const last = pivot.closing_balance_projection_cents.length - 1;
    return pivot.closing_balance_projection_cents[last] ?? null;
  }, [pivot]);

  const variation =
    currentBalance != null && finalBalance != null
      ? finalBalance - currentBalance
      : null;

  return (
    <div className="space-y-2.5">
      {pivot ? (
        <>
          <KpiCard
            label="Trésorerie courante"
            value={currentBalance != null ? formatCents(currentBalance) : "—"}
            hint="Solde de clôture du mois en cours"
            tone="primary"
            icon={<Wallet className="h-3 w-3" />}
          />
          <KpiCard
            label="Projection fin de fenêtre"
            value={finalBalance != null ? formatCents(finalBalance) : "—"}
            hint={`Au ${pivot.months[pivot.months.length - 1] ?? ""}`}
            tone="neutral"
            icon={<Clock className="h-3 w-3" />}
          />
          <KpiCard
            label="Variation prévue"
            value={variation != null ? formatCents(variation) : "—"}
            hint="Δ entre projection et solde courant"
            tone={variation == null ? "neutral" : variation >= 0 ? "positive" : "negative"}
            icon={
              variation != null && variation >= 0 ? (
                <TrendingUp className="h-3 w-3" />
              ) : (
                <TrendingDown className="h-3 w-3" />
              )
            }
          />
        </>
      ) : (
        <>
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </>
      )}

      <div className="my-2 border-t border-line-soft" />

      {wc.isLoading ? (
        <>
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </>
      ) : wc.data?.has_data ? (
        <>
          <KpiCard
            label="DSO"
            value={wc.data.dso_days !== null ? `${wc.data.dso_days} j` : "—"}
            hint="Délai client moyen"
            tooltip="Nombre de jours moyen entre l'émission d'une facture client et son encaissement effectif."
            tone="neutral"
            icon={<Building2 className="h-3 w-3" />}
          />
          <KpiCard
            label="DPO"
            value={wc.data.dpo_days !== null ? `${wc.data.dpo_days} j` : "—"}
            hint="Délai fournisseur moyen"
            tooltip="Nombre de jours moyen entre la réception d'une facture fournisseur et son règlement."
            tone="neutral"
            icon={<Building2 className="h-3 w-3" />}
          />
          <KpiCard
            label="BFR"
            value={wc.data.bfr_cents !== null ? formatCents(wc.data.bfr_cents) : "—"}
            hint="Besoin en fonds de roulement"
            tooltip="Créances clients non encaissées moins dettes fournisseurs non réglées. Positif = vous financez vos clients."
            tone="neutral"
            icon={<Building2 className="h-3 w-3" />}
          />
        </>
      ) : (
        <div className="rounded-md bg-amber-50 px-3 py-2 text-[11.5px] text-amber-900">
          Aucun engagement enregistré : DSO, DPO et BFR indisponibles.
        </div>
      )}
    </div>
  );
}
