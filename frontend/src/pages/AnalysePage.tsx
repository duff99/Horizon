/**
 * AnalysePage — tableau de bord d'indicateurs clés et de dérives.
 *
 * 6 widgets orientés KPI, alimentés par `/api/analysis/*`.
 */
import { useState } from "react";

import { EntitySelector } from "@/components/EntitySelector";
import {
  PeriodSelector,
  defaultPeriodValue,
  type PeriodValue,
} from "@/components/PeriodSelector";
import { CategoryDriftTable } from "@/components/analyse/CategoryDriftTable";
import { ClientConcentrationCard } from "@/components/analyse/ClientConcentrationCard";
import { EntitiesComparisonTable } from "@/components/analyse/EntitiesComparisonTable";
import { RunwayCard } from "@/components/analyse/RunwayCard";
import { TopMoversCard } from "@/components/analyse/TopMoversCard";
import { YoYChart } from "@/components/analyse/YoYChart";
import { useEntityFilter } from "@/stores/entityFilter";

export function AnalysePage() {
  const entityId = useEntityFilter((s) => s.entityId);
  const entityIdForQueries = entityId ?? undefined;

  // Le PeriodSelector est affiché dans l'en-tête pour cohérence visuelle avec
  // les autres pages. Les widgets Analyse ont leurs propres horizons métier
  // (mois courant, 3m, 6m, 12m) et ne dépendent pas directement de `period`.
  const [period, setPeriod] = useState<PeriodValue>(() =>
    defaultPeriodValue("30d"),
  );

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight text-ink">
            Analyse
          </h1>
          <p className="mt-0.5 text-[13px] text-muted-foreground">
            Indicateurs clés, dérives et comparaisons sur les 12 derniers mois.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <EntitySelector />
          <PeriodSelector value={period} onChange={setPeriod} />
        </div>
      </div>

      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12">
          <CategoryDriftTable entityId={entityIdForQueries} />
        </div>
        <div className="col-span-12 md:col-span-6">
          <TopMoversCard entityId={entityIdForQueries} />
        </div>
        <div className="col-span-12 md:col-span-6">
          <RunwayCard entityId={entityIdForQueries} />
        </div>
        <div className="col-span-12 md:col-span-8">
          <YoYChart entityId={entityIdForQueries} />
        </div>
        <div className="col-span-12 md:col-span-4">
          <ClientConcentrationCard entityId={entityIdForQueries} />
        </div>
        <div className="col-span-12">
          <EntitiesComparisonTable />
        </div>
      </div>
    </section>
  );
}
