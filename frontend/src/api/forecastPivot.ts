import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type { PivotResult } from "@/types/forecast";

export interface PivotQueryParams {
  scenarioId: number | null | undefined;
  entityId: number | null | undefined;
  from: string; // YYYY-MM
  to: string; // YYYY-MM
  accountIds?: number[] | null;
}

export function usePivot(params: PivotQueryParams) {
  const { scenarioId, entityId, from, to, accountIds } = params;
  const enabled = scenarioId != null && entityId != null && !!from && !!to;
  return useQuery({
    queryKey: [
      "forecast-pivot",
      scenarioId ?? null,
      entityId ?? null,
      from,
      to,
      accountIds ?? null,
    ],
    queryFn: () => {
      const qp = new URLSearchParams();
      qp.set("scenario_id", String(scenarioId));
      qp.set("entity_id", String(entityId));
      qp.set("from", from);
      qp.set("to", to);
      if (accountIds && accountIds.length > 0) {
        qp.set("accounts", accountIds.join(","));
      }
      return apiFetch<PivotResult>(`/api/forecast/pivot?${qp.toString()}`);
    },
    enabled,
    staleTime: 30_000,
  });
}
