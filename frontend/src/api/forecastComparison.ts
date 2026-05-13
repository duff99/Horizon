import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";

export interface ComparisonRow {
  category_id: number;
  label: string;
  direction: "in" | "out";
  forecast_cents: number;
  realized_cents: number;
  ecart_cents: number;
  ecart_pct: number | null;
  status: "green" | "amber" | "red" | "no-forecast";
}

export interface ComparisonMonth {
  month: string;
  is_snapshotted: boolean;
  rows: ComparisonRow[];
  total_in_forecast_cents: number;
  total_in_realized_cents: number;
  total_out_forecast_cents: number;
  total_out_realized_cents: number;
  net_forecast_cents: number;
  net_realized_cents: number;
}

export interface ComparisonResult {
  months: ComparisonMonth[];
}

export interface ComparisonQueryParams {
  scenarioId: number | null | undefined;
  entityId: number | null | undefined;
  from: string;
  to: string;
}

export function useForecastComparison(params: ComparisonQueryParams) {
  const { scenarioId, entityId, from, to } = params;
  const enabled = scenarioId != null && entityId != null && !!from && !!to;
  return useQuery({
    queryKey: ["forecast-comparison", scenarioId ?? null, entityId ?? null, from, to],
    queryFn: () => {
      const qp = new URLSearchParams();
      qp.set("scenario_id", String(scenarioId));
      qp.set("entity_id", String(entityId));
      qp.set("from", from);
      qp.set("to", to);
      return apiFetch<ComparisonResult>(`/api/forecast/comparison?${qp.toString()}`);
    },
    enabled,
  });
}

export interface SnapshotPayload {
  scenario_id: number;
  entity_id: number;
  month: string;
}

export function useReCloseSnapshot() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (p: SnapshotPayload) =>
      apiFetch<{ snapshotted_count: number }>("/api/forecast/snapshots", {
        method: "POST",
        body: JSON.stringify(p),
      }),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({
        queryKey: ["forecast-comparison", vars.scenario_id],
      });
    },
  });
}
