/**
 * Clients fetch + hooks TanStack Query pour `/api/analysis/*`.
 */
import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "./client";
import type {
  CategoryDriftDetailResponse,
  CategoryDriftResponse,
  ClientConcentrationResponse,
  EntitiesComparisonResponse,
  ForecastVarianceResponse,
  RunwayResponse,
  TopMoversResponse,
  WorkingCapitalResponse,
  YoYResponse,
} from "../types/analysis";

// ---------------------------------------------------------------------------
// Fetchers
// ---------------------------------------------------------------------------

function buildParams(
  entries: Array<[string, string | number | undefined | null]>,
): string {
  const p = new URLSearchParams();
  for (const [k, v] of entries) {
    if (v === undefined || v === null || v === "") continue;
    p.set(k, String(v));
  }
  const s = p.toString();
  return s ? `?${s}` : "";
}

export function fetchCategoryDrift(args: {
  entityId?: number;
  seuilPct?: number;
}): Promise<CategoryDriftResponse> {
  return apiFetch<CategoryDriftResponse>(
    `/api/analysis/category-drift${buildParams([
      ["entity_id", args.entityId],
      ["seuil_pct", args.seuilPct],
    ])}`,
  );
}

export function fetchTopMovers(args: {
  entityId?: number;
  limit?: number;
}): Promise<TopMoversResponse> {
  return apiFetch<TopMoversResponse>(
    `/api/analysis/top-movers${buildParams([
      ["entity_id", args.entityId],
      ["limit", args.limit],
    ])}`,
  );
}

export function fetchRunway(args: { entityId?: number }): Promise<RunwayResponse> {
  return apiFetch<RunwayResponse>(
    `/api/analysis/runway${buildParams([["entity_id", args.entityId]])}`,
  );
}

export function fetchYoY(args: { entityId?: number }): Promise<YoYResponse> {
  return apiFetch<YoYResponse>(
    `/api/analysis/yoy${buildParams([["entity_id", args.entityId]])}`,
  );
}

export function fetchClientConcentration(args: {
  entityId?: number;
  months?: number;
}): Promise<ClientConcentrationResponse> {
  return apiFetch<ClientConcentrationResponse>(
    `/api/analysis/client-concentration${buildParams([
      ["entity_id", args.entityId],
      ["months", args.months],
    ])}`,
  );
}

export function fetchEntitiesComparison(args: {
  months?: number;
}): Promise<EntitiesComparisonResponse> {
  return apiFetch<EntitiesComparisonResponse>(
    `/api/analysis/entities-comparison${buildParams([
      ["months", args.months],
    ])}`,
  );
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

const STALE = 5 * 60_000;

// Les 5 hooks ci-dessous exigent un `entityId` (le backend rejette en 422
// sinon — `entity_id: int = Query(...)` obligatoire). On désactive le fetch
// tant qu'aucune entité n'est sélectionnée, pour éviter les requêtes
// transitoires qui polluent les logs et déclenchent des isError côté UI.
export function useCategoryDrift(args: {
  entityId?: number;
  seuilPct?: number;
}) {
  return useQuery({
    queryKey: ["analysis", "category-drift", args.entityId, args.seuilPct],
    queryFn: () => fetchCategoryDrift(args),
    staleTime: STALE,
    enabled: args.entityId !== undefined,
  });
}

export function useTopMovers(args: { entityId?: number; limit?: number }) {
  return useQuery({
    queryKey: ["analysis", "top-movers", args.entityId, args.limit],
    queryFn: () => fetchTopMovers(args),
    staleTime: STALE,
    enabled: args.entityId !== undefined,
  });
}

export function useRunway(args: { entityId?: number }) {
  return useQuery({
    queryKey: ["analysis", "runway", args.entityId],
    queryFn: () => fetchRunway(args),
    staleTime: STALE,
    enabled: args.entityId !== undefined,
  });
}

export function useYoY(args: { entityId?: number }) {
  return useQuery({
    queryKey: ["analysis", "yoy", args.entityId],
    queryFn: () => fetchYoY(args),
    staleTime: STALE,
    enabled: args.entityId !== undefined,
  });
}

export function useClientConcentration(args: {
  entityId?: number;
  months?: number;
}) {
  return useQuery({
    queryKey: ["analysis", "client-concentration", args.entityId, args.months],
    queryFn: () => fetchClientConcentration(args),
    staleTime: STALE,
    enabled: args.entityId !== undefined,
  });
}

export function useEntitiesComparison(args: { months?: number } = {}) {
  return useQuery({
    queryKey: ["analysis", "entities-comparison", args.months],
    queryFn: () => fetchEntitiesComparison(args),
    staleTime: STALE,
  });
}

// ---------------------------------------------------------------------------
// Drill-down + Variance + BFR (nouveaux endpoints 2026-04)
// ---------------------------------------------------------------------------

export function fetchCategoryDriftDetail(args: {
  categoryId: number;
  entityId: number;
}): Promise<CategoryDriftDetailResponse> {
  return apiFetch<CategoryDriftDetailResponse>(
    `/api/analysis/category-drift/${args.categoryId}/transactions${buildParams([
      ["entity_id", args.entityId],
    ])}`,
  );
}

export function useCategoryDriftDetail(args: {
  categoryId: number | null;
  entityId?: number;
}) {
  return useQuery({
    queryKey: [
      "analysis",
      "category-drift-detail",
      args.categoryId,
      args.entityId,
    ],
    queryFn: () =>
      fetchCategoryDriftDetail({
        categoryId: args.categoryId as number,
        entityId: args.entityId as number,
      }),
    staleTime: STALE,
    enabled: args.categoryId !== null && args.entityId !== undefined,
  });
}

export function fetchForecastVariance(args: {
  entityId?: number;
  months?: number;
}): Promise<ForecastVarianceResponse> {
  return apiFetch<ForecastVarianceResponse>(
    `/api/analysis/forecast-variance${buildParams([
      ["entity_id", args.entityId],
      ["months", args.months],
    ])}`,
  );
}

export function useForecastVariance(args: {
  entityId?: number;
  months?: number;
}) {
  return useQuery({
    queryKey: [
      "analysis",
      "forecast-variance",
      args.entityId,
      args.months,
    ],
    queryFn: () => fetchForecastVariance(args),
    staleTime: STALE,
    enabled: args.entityId !== undefined,
  });
}

export function fetchWorkingCapital(args: {
  entityId?: number;
}): Promise<WorkingCapitalResponse> {
  return apiFetch<WorkingCapitalResponse>(
    `/api/analysis/working-capital${buildParams([
      ["entity_id", args.entityId],
    ])}`,
  );
}

export function useWorkingCapital(args: { entityId?: number }) {
  return useQuery({
    queryKey: ["analysis", "working-capital", args.entityId],
    queryFn: () => fetchWorkingCapital(args),
    staleTime: STALE,
    enabled: args.entityId !== undefined,
  });
}
