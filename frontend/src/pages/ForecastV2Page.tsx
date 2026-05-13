import { useEffect, useMemo, useState } from "react";
import { todayISO } from "@/api/exports";
import { ExportButton } from "@/components/ExportButton";
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
import { ComparisonPanel } from "@/components/forecast/ComparisonPanel";
import { PivotBars } from "@/components/forecast/PivotBars";
import { PivotTable } from "@/components/forecast/PivotTable";
import { CellEditorDrawer } from "@/components/forecast/CellEditorDrawer";
import { ForecastKpiSidebar } from "@/components/forecast/ForecastKpiSidebar";
import { Rolling13WChart } from "@/components/forecast/Rolling13WChart";
import {
  ScenarioOverlayMenu,
  useScenarioOverlays,
} from "@/components/forecast/ScenarioOverlay";
import { currentMonthStr, shiftMonth } from "@/lib/forecastFormat";

interface DrawerState {
  month: string;
  categoryId: number;
  /** Direction de la ligne cliquée — détermine le signe attendu pour la
   * saisie ("in" → positif, "out" → négatif). Le formulaire signe
   * automatiquement la valeur saisie. */
  direction: "in" | "out";
}

export function ForecastV2Page() {
  const entityId = useEntityFilter((s) => s.entityId);
  const setEntityId = useEntityFilter((s) => s.setEntityId);
  const scenarioId = useForecastUi((s) => s.scenarioId);
  const accountIds = useForecastUi((s) => s.accountIds);

  const entitiesQuery = useEntities();
  const entities = entitiesQuery.data ?? [];

  // Politique 2026-04 (cohérente avec AnalysePage) : pas de vue "Toutes les
  // sociétés" sur Prévisionnel — chaque entité a son scénario propre, agréger
  // n'a pas de sens financier. On auto-sélectionne la 1ère entité accessible
  // (ordre alphabétique côté API) si rien n'est sélectionné.
  useEffect(() => {
    if (entityId === null && entities.length > 0) {
      setEntityId(entities[0].id);
    }
  }, [entityId, entities, setEntityId]);

  const effectiveEntityId = entityId;

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

  // Toggle vue : Plan (pivot prévisionnel) vs Suivi des écarts (snapshot
  // comparé au réalisé). Même scénario, même plage, même entité.
  const [view, setView] = useState<"plan" | "tracking">("plan");

  // G7 — Overlays multi-scénarios. État dans la page, fetch côté hook.
  const [overlayIds, setOverlayIds] = useState<number[]>([]);
  const toggleOverlay = (id: number) =>
    setOverlayIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  const overlays = useScenarioOverlays({
    entityId: effectiveEntityId,
    currentScenarioId: scenarioId,
    from: period.from,
    to: period.to,
    accountIds,
    visibleIds: overlayIds,
  });
  const overlaySeries = useMemo(
    () =>
      overlays.items
        .filter((it) => it.result != null)
        .map((it) => ({
          scenarioId: it.scenarioId,
          name: it.name,
          color: it.color,
          result: it.result!,
        })),
    [overlays.items],
  );

  const noEntity = effectiveEntityId == null;
  const noScenario =
    !scenariosQuery.isLoading &&
    (scenariosQuery.data?.length ?? 0) === 0 &&
    !noEntity;
  // Reader sans aucune entité accordée → message explicite (cf. AnalysePage)
  const noEntityAtAll =
    entitiesQuery.isSuccess && entities.length === 0;

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 data-page-title className="text-[22px] font-semibold tracking-tight text-ink">
            Prévisionnel de trésorerie
          </h1>
          <p className="mt-0.5 text-[13px] text-muted-foreground">
            Pivot catégorie × mois, sur 15 mois glissants (3 passés + 12 à
            venir).
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <EntitySelector allowAll={false} />
          <ScenarioSelector entityId={effectiveEntityId} />
          <ConsolidatedAccountsPopover entityId={effectiveEntityId} />
          <PeriodSelector
            value={period}
            onChange={setPeriod}
            granularity="month"
          />
          {/* G7 — menu Comparer (multi-overlay) */}
          {!noEntity && !noScenario && (
            <ScenarioOverlayMenu
              entityId={effectiveEntityId}
              currentScenarioId={scenarioId}
              visibleIds={overlayIds}
              onToggle={toggleOverlay}
            />
          )}
        </div>
      </div>

      {noEntityAtAll && (
        <div
          role="alert"
          className="rounded-md bg-amber-50 px-4 py-3 text-[13px] text-amber-900"
        >
          Tu n'as accès à aucune société pour le moment. Demande à un
          administrateur de t'accorder un accès.
        </div>
      )}

      {!noEntityAtAll && noEntity && (
        <div className="rounded-xl border border-line-soft bg-panel p-10 text-center text-[13px] text-muted-foreground shadow-card">
          Chargement de votre société par défaut…
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

      {/* Toggle Plan ↔ Suivi des écarts */}
      {!noEntity && !noScenario && (
        <div className="inline-flex rounded-md border border-line-soft bg-panel p-0.5 shadow-card">
          <button
            type="button"
            onClick={() => setView("plan")}
            className={`rounded-sm px-3 py-1.5 text-[12.5px] font-medium transition-colors ${
              view === "plan"
                ? "bg-accent text-white"
                : "text-ink-2 hover:text-ink"
            }`}
            title="Vue prévisionnelle : pivot catégorie × mois, saisie des règles et simulation."
          >
            Plan
          </button>
          <button
            type="button"
            onClick={() => setView("tracking")}
            className={`rounded-sm px-3 py-1.5 text-[12.5px] font-medium transition-colors ${
              view === "tracking"
                ? "bg-accent text-white"
                : "text-ink-2 hover:text-ink"
            }`}
            title="Comparaison prévu (figé au passage du mois) vs réalisé (transactions importées) sur les mois clôturés."
          >
            Suivi des écarts
          </button>
        </div>
      )}

      {!noEntity && !noScenario && view === "tracking" && (
        <ComparisonPanel
          scenarioId={scenarioId}
          entityId={effectiveEntityId ?? null}
          from={period.from}
          to={period.to}
        />
      )}

      {!noEntity &&
        !noScenario &&
        view === "plan" &&
        pivotQuery.data &&
        effectiveEntityId != null && (
          <div className="grid gap-4 lg:grid-cols-[220px,minmax(0,1fr)]">
            {/* Colonne gauche : cartes KPI sticky */}
            <aside className="lg:sticky lg:top-4 lg:self-start">
              <ForecastKpiSidebar
                entityId={effectiveEntityId}
                pivot={pivotQuery.data}
                currentMonth={currentMonth}
              />
            </aside>

            {/* Colonne droite : graphique + pivot + rolling */}
            <div className="min-w-0 space-y-4">
              <div className="rounded-xl border border-line-soft bg-panel p-4 shadow-card">
                <div className="mb-2 flex flex-wrap items-baseline justify-between gap-y-1">
                  <h2 className="text-[13px] font-semibold text-ink">
                    Encaissements vs. décaissements
                  </h2>
                  <span className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
                    <span>Hachures = prévisionnel · ligne = solde projeté</span>
                    {overlaySeries.map((ov) => (
                      <span
                        key={ov.scenarioId}
                        className="inline-flex items-center gap-1"
                      >
                        <span
                          aria-hidden
                          className="inline-block h-2 w-2 rounded-full"
                          style={{ background: ov.color }}
                        />
                        {ov.name}
                      </span>
                    ))}
                  </span>
                </div>
                <PivotBars
                  result={pivotQuery.data}
                  currentMonth={currentMonth}
                  overlays={overlaySeries}
                />
              </div>

              <div>
                <PivotTable
                  result={pivotQuery.data}
                  onCellClick={(month, categoryId, direction) =>
                    setDrawer({ month, categoryId, direction })
                  }
                  currentMonth={currentMonth}
                />
                {scenarioId != null && (
                  <div className="mt-2 flex justify-end">
                    <ExportButton
                      url={`/api/forecast/pivot/export?scenario_id=${scenarioId}&entity_id=${effectiveEntityId}&from=${period.from}&to=${period.to}${accountIds && accountIds.length > 0 ? `&accounts=${accountIds.join(",")}` : ""}`}
                      filename={`previsionnel-pivot_${todayISO()}.csv`}
                      label="Exporter le pivot CSV"
                    />
                  </div>
                )}
              </div>

              <div className="rounded-xl border border-line-soft bg-panel p-4 shadow-card">
                <Rolling13WChart
                  entityId={effectiveEntityId}
                  scenarioId={scenarioId}
                />
              </div>
            </div>
          </div>
        )}

      {drawer && effectiveEntityId != null && scenarioId != null && (
        <CellEditorDrawer
          open
          month={drawer.month}
          categoryId={drawer.categoryId}
          direction={drawer.direction}
          entityId={effectiveEntityId}
          scenarioId={scenarioId}
          accountIds={accountIds}
          onClose={() => setDrawer(null)}
        />
      )}
    </section>
  );
}
