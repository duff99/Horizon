/**
 * WorkingCapitalCard — KPI de besoin en fonds de roulement.
 *
 * Trois indicateurs combinés :
 *   - DSO (Days Sales Outstanding) : délai moyen pour qu'un client paie
 *   - DPO (Days Payable Outstanding) : délai moyen avant qu'on paie un fournisseur
 *   - BFR (Besoin en Fonds de Roulement) : créances en cours moins dettes en cours
 *
 * Calculé à partir des engagements (Commitments) appariés. Si aucun
 * engagement n'a été saisi, état vide avec un lien vers Engagements.
 */
import { memo } from "react";
import { Link } from "react-router-dom";

import { useWorkingCapital } from "@/api/analysis";
import { formatCents } from "@/lib/forecastFormat";

interface Props {
  entityId?: number;
}

function Skeleton() {
  return (
    <div className="grid grid-cols-3 gap-3">
      <div className="h-20 animate-pulse rounded bg-slate-100" />
      <div className="h-20 animate-pulse rounded bg-slate-100" />
      <div className="h-20 animate-pulse rounded bg-slate-100" />
    </div>
  );
}

function WorkingCapitalCardInner({ entityId }: Props) {
  const query = useWorkingCapital({ entityId });
  const data = query.data;

  return (
    <div className="rounded-xl border border-line-soft bg-panel p-5 shadow-card">
      <div className="mb-4">
        <div className="text-[15px] font-semibold text-ink">
          Besoin en fonds de roulement (BFR)
        </div>
        <div className="mt-0.5 text-[12.5px] text-muted-foreground">
          Mesure l'argent immobilisé dans le cycle d'exploitation : ce que
          vos clients vous doivent encore, moins ce que vous devez à vos
          fournisseurs.
        </div>
      </div>

      {query.isLoading ? (
        <Skeleton />
      ) : query.isError ? (
        <div
          role="alert"
          className="rounded-md bg-rose-50 px-3 py-2 text-[12.5px] text-rose-900"
        >
          Impossible de calculer le BFR.
        </div>
      ) : !data?.has_data ? (
        <div className="rounded-md border border-dashed border-line-soft bg-panel-2/40 p-6 text-center">
          <div className="text-[13px] font-medium text-ink">
            Aucun engagement saisi pour cette société.
          </div>
          <div className="mt-1 text-[12.5px] text-muted-foreground">
            Saisissez vos factures et paiements à venir sur la page
            Engagements pour activer le suivi DSO / DPO / BFR.
          </div>
          <Link
            to="/engagements"
            className="mt-3 inline-flex rounded-md bg-accent px-3 py-1.5 text-[12.5px] font-medium text-white hover:bg-accent/90"
          >
            Aller aux Engagements
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <Metric
              label="Délai moyen de paiement client"
              acronym="DSO"
              value={data.dso_days != null ? `${data.dso_days} j` : "—"}
              hint={
                data.dso_days == null
                  ? `${data.matched_in_count}/3 paiements appariés (besoin ≥ 3)`
                  : `Sur ${data.matched_in_count} paiements clients`
              }
            />
            <Metric
              label="Délai moyen de paiement fournisseur"
              acronym="DPO"
              value={data.dpo_days != null ? `${data.dpo_days} j` : "—"}
              hint={
                data.dpo_days == null
                  ? `${data.matched_out_count}/3 paiements appariés (besoin ≥ 3)`
                  : `Sur ${data.matched_out_count} paiements fournisseurs`
              }
            />
            <Metric
              label="Besoin en fonds de roulement"
              acronym="BFR"
              value={data.bfr_cents != null ? formatCents(data.bfr_cents) : "—"}
              hint="Créances clients en cours − Dettes fournisseurs en cours"
              accent={
                data.bfr_cents != null && data.bfr_cents > 0 ? "warning" : "ok"
              }
            />
          </div>
          <dl className="grid grid-cols-2 gap-2 text-[12.5px]">
            <div className="rounded-md bg-panel-2/40 p-2">
              <dt className="text-muted-foreground">Créances clients à encaisser</dt>
              <dd className="mt-0.5 font-mono tabular-nums text-emerald-700">
                {formatCents(data.receivables_cents)}
              </dd>
            </div>
            <div className="rounded-md bg-panel-2/40 p-2">
              <dt className="text-muted-foreground">Dettes fournisseurs à payer</dt>
              <dd className="mt-0.5 font-mono tabular-nums text-rose-700">
                {formatCents(data.payables_cents)}
              </dd>
            </div>
          </dl>
        </div>
      )}
    </div>
  );
}

interface MetricProps {
  label: string;
  acronym: string;
  value: string;
  hint: string;
  accent?: "ok" | "warning";
}

function Metric({ label, acronym, value, hint, accent }: MetricProps) {
  const ring =
    accent === "warning" ? "border-amber-200 bg-amber-50/30" : "border-line-soft";
  return (
    <div className={`rounded-md border p-3 ${ring}`}>
      <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        {label}{" "}
        <span className="font-normal text-muted-foreground/80">
          ({acronym})
        </span>
      </div>
      <div className="mt-1 font-mono text-[20px] font-semibold tabular-nums text-ink">
        {value}
      </div>
      <div className="mt-1 text-[11.5px] text-muted-foreground">{hint}</div>
    </div>
  );
}

export const WorkingCapitalCard = memo(WorkingCapitalCardInner);
