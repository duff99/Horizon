/**
 * ScenarioOverlay — sélecteur pour comparer un second scénario en overlay.
 *
 * Expose un hook `useScenarioOverlay` et un composant `ScenarioOverlaySelect`
 * qui liste les scénarios disponibles (hors scénario courant).
 *
 * Aucune modification backend — les scénarios existent déjà en DB.
 */
import { useState } from "react";
import { useScenarios } from "@/api/forecastScenarios";
import { usePivot, type PivotQueryParams } from "@/api/forecastPivot";
import type { PivotResult } from "@/types/forecast";

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export interface ScenarioOverlayParams {
  entityId: number | null | undefined;
  currentScenarioId: number | null | undefined;
  from: string;
  to: string;
  accountIds?: number[] | null;
}

export interface ScenarioOverlayResult {
  overlayScenarioId: number | null;
  setOverlayScenarioId: (id: number | null) => void;
  overlayPivot: PivotResult | undefined;
  isLoading: boolean;
}

export function useScenarioOverlay(
  params: ScenarioOverlayParams,
): ScenarioOverlayResult {
  const [overlayScenarioId, setOverlayScenarioId] = useState<number | null>(
    null,
  );

  const pivotParams: PivotQueryParams = {
    scenarioId: overlayScenarioId,
    entityId: params.entityId,
    from: params.from,
    to: params.to,
    accountIds: params.accountIds,
  };

  const overlayQuery = usePivot(pivotParams);

  return {
    overlayScenarioId,
    setOverlayScenarioId,
    overlayPivot: overlayQuery.data,
    isLoading: overlayQuery.isLoading,
  };
}

// ---------------------------------------------------------------------------
// Composant sélecteur
// ---------------------------------------------------------------------------

interface ScenarioOverlaySelectProps {
  entityId: number | null | undefined;
  currentScenarioId: number | null | undefined;
  overlayScenarioId: number | null;
  onSelect: (id: number | null) => void;
}

export function ScenarioOverlaySelect({
  entityId,
  currentScenarioId,
  overlayScenarioId,
  onSelect,
}: ScenarioOverlaySelectProps) {
  const scenariosQuery = useScenarios(entityId);
  const scenarios = (scenariosQuery.data ?? []).filter(
    (s) => s.id !== currentScenarioId,
  );

  if (scenarios.length === 0) return null;

  return (
    <div className="flex items-center gap-2">
      <label className="text-[12px] font-medium text-muted-foreground whitespace-nowrap">
        Comparer avec :
      </label>
      <select
        value={overlayScenarioId ?? ""}
        onChange={(e) =>
          onSelect(e.target.value ? Number(e.target.value) : null)
        }
        className="rounded-md border border-line-soft bg-panel px-2 py-1 text-[12px] text-ink shadow-sm focus:outline-none focus:ring-1 focus:ring-accent"
      >
        <option value="">— Aucun —</option>
        {scenarios.map((s) => (
          <option key={s.id} value={s.id}>
            {s.name}
          </option>
        ))}
      </select>
      <span
        title="Superpose les flux d'un second scénario sur le graphique pour visualiser l'écart entre deux hypothèses."
        className="cursor-help text-[11px] text-muted-foreground"
      >
        ?
      </span>
    </div>
  );
}
