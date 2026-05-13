/**
 * ScenarioOverlay — sélecteur multi-scénarios pour comparer plusieurs
 * hypothèses simultanément sur le graphique.
 *
 * Expose :
 * - `colorForScenario(id)` : couleur stable par scénario (palette de 6).
 * - `useScenarioOverlays` : hook qui gère les ids visibles et fetche
 *   leurs pivots en parallèle via `useQueries`.
 * - `ScenarioOverlayMenu` : Popover listant les scénarios disponibles
 *   avec un toggle œil par ligne.
 *
 * Aucune modification backend — les scénarios existent déjà en DB.
 */
import { useMemo, useState } from "react";
import { useQueries } from "@tanstack/react-query";
import { Eye, EyeOff, Layers } from "lucide-react";
import { useScenarios } from "@/api/forecastScenarios";
import { apiFetch } from "@/api/client";
import type { PivotResult } from "@/types/forecast";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Palette
// ---------------------------------------------------------------------------

/**
 * Palette de 6 couleurs pour les overlays. Volontairement distinctes de
 * l'accent bleu (réservé au scénario actif) et des couleurs entrées/sorties.
 */
const OVERLAY_PALETTE = [
  "#f59e0b", // amber-500
  "#8b5cf6", // violet-500
  "#06b6d4", // cyan-500
  "#ec4899", // pink-500
  "#84cc16", // lime-500
  "#f97316", // orange-500
];

/** Couleur stable pour un scénario donné — hash de l'id sur la palette. */
export function colorForScenario(scenarioId: number): string {
  const idx = ((scenarioId % OVERLAY_PALETTE.length) + OVERLAY_PALETTE.length) %
    OVERLAY_PALETTE.length;
  return OVERLAY_PALETTE[idx];
}

// ---------------------------------------------------------------------------
// Hook : fetch multi-pivots
// ---------------------------------------------------------------------------

export interface ScenarioOverlaysParams {
  entityId: number | null | undefined;
  currentScenarioId: number | null | undefined;
  from: string;
  to: string;
  accountIds?: number[] | null;
  visibleIds: number[];
}

export interface OverlayItem {
  scenarioId: number;
  name: string;
  color: string;
  result: PivotResult | undefined;
}

export interface UseScenarioOverlaysResult {
  items: OverlayItem[];
  isLoadingAny: boolean;
}

export function useScenarioOverlays(
  params: ScenarioOverlaysParams,
): UseScenarioOverlaysResult {
  const { entityId, from, to, accountIds, visibleIds } = params;
  const scenariosQuery = useScenarios(entityId);
  const scenarios = scenariosQuery.data ?? [];

  const queries = useQueries({
    queries: visibleIds.map((id) => ({
      queryKey: [
        "forecast-pivot",
        id,
        entityId ?? null,
        from,
        to,
        accountIds ?? null,
      ],
      queryFn: () => {
        const qp = new URLSearchParams();
        qp.set("scenario_id", String(id));
        qp.set("entity_id", String(entityId));
        qp.set("from", from);
        qp.set("to", to);
        if (accountIds && accountIds.length > 0) {
          qp.set("accounts", accountIds.join(","));
        }
        return apiFetch<PivotResult>(`/api/forecast/pivot?${qp.toString()}`);
      },
      enabled: entityId != null && !!from && !!to,
    })),
  });

  const items = useMemo<OverlayItem[]>(() => {
    return visibleIds.map((id, idx) => {
      const sc = scenarios.find((s) => s.id === id);
      return {
        scenarioId: id,
        name: sc?.name ?? `Scénario ${id}`,
        color: colorForScenario(id),
        result: queries[idx]?.data,
      };
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visibleIds, scenarios, queries.map((q) => q.dataUpdatedAt).join(",")]);

  return {
    items,
    isLoadingAny: queries.some((q) => q.isLoading),
  };
}

// ---------------------------------------------------------------------------
// Composant menu (Popover)
// ---------------------------------------------------------------------------

interface ScenarioOverlayMenuProps {
  entityId: number | null | undefined;
  currentScenarioId: number | null | undefined;
  visibleIds: number[];
  onToggle: (id: number) => void;
}

export function ScenarioOverlayMenu({
  entityId,
  currentScenarioId,
  visibleIds,
  onToggle,
}: ScenarioOverlayMenuProps) {
  const [open, setOpen] = useState(false);
  const scenariosQuery = useScenarios(entityId);
  const others = (scenariosQuery.data ?? []).filter(
    (s) => s.id !== currentScenarioId,
  );

  const count = visibleIds.length;
  const buttonLabel =
    count === 0 ? "Comparer scénarios" : `Comparer (${count})`;

  if (others.length === 0) return null;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          className={cn(
            "h-8 gap-1.5 px-3 text-[12px]",
            count > 0 && "border-accent text-accent",
          )}
          title="Superpose les flux d'un ou plusieurs autres scénarios sur le graphique pour visualiser les écarts."
        >
          <Layers className="h-3.5 w-3.5" aria-hidden />
          {buttonLabel}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-72 p-2">
        <div className="px-2 py-1 text-[10.5px] font-semibold uppercase tracking-wider text-muted-foreground">
          Scénarios à superposer
        </div>
        <ul className="space-y-0.5">
          {others.map((s) => {
            const visible = visibleIds.includes(s.id);
            const color = colorForScenario(s.id);
            return (
              <li key={s.id}>
                <button
                  type="button"
                  onClick={() => onToggle(s.id)}
                  className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-[12.5px] text-ink hover:bg-panel-2"
                  aria-pressed={visible}
                >
                  <span
                    aria-hidden
                    className="inline-block h-2.5 w-2.5 shrink-0 rounded-full"
                    style={{ background: color }}
                  />
                  <span className="flex-1 truncate">{s.name}</span>
                  {visible ? (
                    <Eye
                      className="h-3.5 w-3.5 text-accent"
                      aria-label="Visible"
                    />
                  ) : (
                    <EyeOff
                      className="h-3.5 w-3.5 text-muted-foreground"
                      aria-label="Masqué"
                    />
                  )}
                </button>
              </li>
            );
          })}
        </ul>
        <p className="mt-2 border-t border-line-soft px-2 pt-2 text-[10.5px] leading-snug text-muted-foreground">
          Chaque scénario est tracé en pointillés de sa couleur sur le
          graphique. Le scénario actif (bleu plein) pilote toujours le tableau.
        </p>
      </PopoverContent>
    </Popover>
  );
}
