/**
 * WorkingCapitalBanner — bandeau DSO/DPO/BFR en tête de ForecastV2Page.
 *
 * Réutilise le hook `useWorkingCapital` existant (api/analysis.ts).
 * Aucune modification backend nécessaire (endpoint déjà exposé).
 */
import { useWorkingCapital } from "@/api/analysis";
import { formatCents } from "@/lib/forecastFormat";

interface Props {
  entityId: number;
}

function KpiCard({
  label,
  value,
  tooltip,
}: {
  label: string;
  value: string;
  tooltip: string;
}) {
  return (
    <div className="flex min-w-[160px] flex-col gap-0.5 rounded-lg border border-line-soft bg-panel px-4 py-2.5 shadow-sm">
      <div className="flex items-center gap-1">
        <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
          {label}
        </span>
        <span
          title={tooltip}
          className="cursor-help text-[11px] text-muted-foreground"
        >
          ?
        </span>
      </div>
      <span className="font-mono text-[20px] font-semibold tabular-nums text-ink">
        {value}
      </span>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="h-[66px] min-w-[160px] animate-pulse rounded-lg border border-line-soft bg-panel-2/40" />
  );
}

export function WorkingCapitalBanner({ entityId }: Props) {
  const q = useWorkingCapital({ entityId });

  if (q.isLoading) {
    return (
      <div className="flex flex-wrap gap-3">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  if (!q.data) return null;

  const { dso_days, dpo_days, bfr_cents, has_data } = q.data;

  if (!has_data) {
    return (
      <div className="rounded-md bg-amber-50 px-4 py-3 text-[13px] text-amber-900">
        Aucun engagement enregistré. Ajoutez des engagements (page Engagements)
        pour calculer DSO, DPO et BFR.
      </div>
    );
  }

  const tooltipInsuffisant =
    "Insuffisant : nécessite des engagements matchés à des transactions.";

  return (
    <div className="flex flex-wrap gap-3">
      <KpiCard
        label="DSO — Délai client moyen"
        value={dso_days !== null ? `${dso_days} j` : "—"}
        tooltip={
          dso_days !== null
            ? "Nombre de jours moyen entre l'émission d'une facture client et son encaissement effectif."
            : tooltipInsuffisant
        }
      />
      <KpiCard
        label="DPO — Délai fournisseur moyen"
        value={dpo_days !== null ? `${dpo_days} j` : "—"}
        tooltip={
          dpo_days !== null
            ? "Nombre de jours moyen entre la réception d'une facture fournisseur et son règlement."
            : tooltipInsuffisant
        }
      />
      <KpiCard
        label="BFR — Besoin en fonds de roulement"
        value={bfr_cents !== null ? formatCents(bfr_cents) : "—"}
        tooltip={
          bfr_cents !== null
            ? "Créances clients non encaissées moins dettes fournisseurs non réglées. Positif = vous financez vos clients."
            : tooltipInsuffisant
        }
      />
    </div>
  );
}
