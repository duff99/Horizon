/**
 * Clients fetch + hooks TanStack Query pour /api/analysis/seasonality (G9).
 */
import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "./client";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SeasonalityPoint {
  month: string;      // "YYYY-MM"
  year: number;
  month_num: number;  // 1-12
  amount_cents: number;
}

export interface SeasonalityResponse {
  entity_id: number;
  category_id: number;
  category_label: string;
  months_available: number;
  has_enough_data: boolean;
  earliest_available: string | null; // "YYYY-MM"
  points: SeasonalityPoint[];
}

// ---------------------------------------------------------------------------
// Fetchers
// ---------------------------------------------------------------------------

export function fetchSeasonality(args: {
  entityId: number;
  categoryId: number;
}): Promise<SeasonalityResponse> {
  return apiFetch<SeasonalityResponse>(
    `/api/analysis/seasonality?entity_id=${args.entityId}&category_id=${args.categoryId}`,
  );
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useSeasonality(args: {
  entityId?: number;
  categoryId?: number;
}) {
  return useQuery({
    queryKey: ["analysis", "seasonality", args.entityId, args.categoryId],
    queryFn: () =>
      fetchSeasonality({
        entityId: args.entityId!,
        categoryId: args.categoryId!,
      }),
    staleTime: 5 * 60_000,
    enabled: args.entityId !== undefined && args.categoryId !== undefined,
  });
}
