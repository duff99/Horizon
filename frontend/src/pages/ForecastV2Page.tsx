import { useMemo, useState } from "react";
import { EntitySelector } from "@/components/EntitySelector";
import {
  PeriodSelector,
  type PeriodValue,
} from "@/components/PeriodSelector";
import { useEntityFilter } from "@/stores/entityFilter";
import { useEntities } from "@/api/entities";
import { useScenarios } from "@/api/forecastScenarios";
import { usePivot } from "@/api/forecastPivot";
import { useForecastUi } from "@/stores/forecastUi";
import { ScenarioSelector } from "@/components/forecast/ScenarioSelector";
import { ConsolidatedAccountsPopover } from "@/components/forecast/ConsolidatedAccountsPopover";
import { PivotBars } from "@/components/forecast/PivotBars";
import { PivotTable } from "@/components/forecast/PivotTable";
import { CellEditorDrawer } from "@/components/forecast/CellEditorDrawer";
import { currentMonthStr, shiftMonth } from "@/lib/forecastFormat";

interface DrawerState {
  month: string;
  categoryId: number;
}

export function ForecastV2Page() {
  const entityId = useEntityFilter((s) => s.entityId);
  const scenarioId = useForecastUi((s) => s.scenarioId);
  const accountIds = useForecastUi((s) => s.accountIds);

  const entitiesQuery = useEntities();
  // If no entity chosen globally but user has exactly 1 accessible, pick it
  const effectiveEntityId = useMemo(() => {
    if (entityId != null) return entityId;
    const entities = entitiesQuery.data ?? [];
    return entities.length === 1 ? entities[0].id : null;
  }, [entityId, entitiesQuery.data]);

  const scenariosQuery = useScenarios(effectiveEntityId);

  // 15-month window par défaut: current - 3, current + 11 (inclusif = 15 mois)
  const currentMonth = useMemo(() => currentMonthStr(), []);
  const defaultFrom = useMemo(
    () => shiftMonth(currentMonth, -3),
    [currentMonth],
  );
  const defaultTo = useMemo(
    () => shiftMonth(currentMonth, 11),
    [currentMonth],
  );

  const [period, setPeriod] = useState<PeriodValue>(() => ({
    from: defaultFrom,
    to: defaultTo,
    preset: "custom",
  }));

  const pivotQuery = usePivot({
    scenarioId,
    entityId: effectiveEntityId,
    from: period.from,
    to: period.to,
    accountIds,
  });

  const [drawer, setDrawer] = useState<DrawerState | null>(null);

  const noEntity = effectiveEntityId == null;
  const noScenario =
    !scenariosQuery.isLoading &&
    (scenariosQuery.data?.length ?? 0) === 0 &&
    !noEntity;

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight text-ink">
            Prévisionnel de trésorerie
          </h1>
          <p className="mt-0.5 text-[13px] text-muted-foreground">
            Pivot catégorie × mois, sur 15 mois glissants (3 passés + 12 à
            venir).
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <EntitySelector />
          <ScenarioSelector entityId={effectiveEntityId} />
          <ConsolidatedAccountsPopover entityId={effectiveEntityId} />
          <PeriodSelector
            value={period}
            onChange={setPeriod}
            granularity="month"
          />
        </div>
      </div>

      {noEntity && (
        <div className="rounded-xl border border-line-soft bg-panel p-10 text-center text-[13px] text-muted-foreground shadow-card">
          Sélectionnez une société pour afficher le prévisionnel.
        </div>
      )}

      {noScenario && (
        <div className="rounded-xl border border-line-soft bg-panel p-10 text-center text-[13px] text-muted-foreground shadow-card">
          Créez votre premier scénario dans le menu ci-dessus pour démarrer.
        </div>
      )}

      {!noEntity && !noScenario && pivotQuery.isError && (
        <div
          role="alert"
          className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-[13px] text-rose-700"
        >
          Erreur lors du chargement du pivot :{" "}
          {pivotQuery.error instanceof Error
            ? pivotQuery.error.message
            : "erreur inconnue"}
        </div>
      )}

      {!noEntity && !noScenario && pivotQuery.isLoading && (
        <div className="space-y-4">
          <div className="h-[260px] animate-pulse rounded-xl border border-line-soft bg-panel-2/40 shadow-card" />
          <div className="h-[320px] animate-pulse rounded-xl border border-line-soft bg-panel-2/40 shadow-card" />
        </div>
      )}

      {!noEntity && !noScenario && pivotQuery.data && (
        <>
          <div className="rounded-xl border border-line-soft bg-panel p-4 shadow-card">
            <div className="mb-2 flex items-baseline justify-between">
              <h2 className="text-[13px] font-semibold text-ink">
                Encaissements vs. décaissements
              </h2>
              <span className="text-[11px] text-muted-foreground">
                Hachures = prévisionnel · ligne = solde projeté
              </span>
            </div>
            <PivotBars
              result={pivotQuery.data}
              currentMonth={currentMonth}
            />
          </div>

          <PivotTable
            result={pivotQuery.data}
            onCellClick={(month, categoryId) =>
              setDrawer({ month, categoryId })
            }
            currentMonth={currentMonth}
          />
        </>
      )}

      {drawer && effectiveEntityId != null && scenarioId != null && (
        <CellEditorDrawer
          open
          month={drawer.month}
          categoryId={drawer.categoryId}
          entityId={effectiveEntityId}
          scenarioId={scenarioId}
          accountIds={accountIds}
          onClose={() => setDrawer(null)}
        />
      )}
    </section>
  );
}
