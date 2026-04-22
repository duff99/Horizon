import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type {
  ForecastLine,
  LineUpsert,
  ValidateFormulaResponse,
} from "@/types/forecast";

export function useLines(scenarioId: number | null | undefined) {
  return useQuery({
    queryKey: ["forecast-lines", scenarioId ?? null],
    queryFn: () =>
      apiFetch<ForecastLine[]>(
        `/api/forecast/lines?scenario_id=${scenarioId}`,
      ),
    enabled: scenarioId != null,
  });
}

export function useUpsertLine() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: LineUpsert) =>
      apiFetch<ForecastLine>("/api/forecast/lines", {
        method: "PUT",
        body: JSON.stringify(payload),
      }),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["forecast-lines", vars.scenario_id] });
      qc.invalidateQueries({ queryKey: ["forecast-pivot"] });
    },
  });
}

export function useDeleteLine() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch<void>(`/api/forecast/lines/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["forecast-lines"] });
      qc.invalidateQueries({ queryKey: ["forecast-pivot"] });
    },
  });
}

export function useValidateFormula() {
  return useMutation({
    mutationFn: (payload: {
      scenario_id: number;
      formula_expr: string;
      category_id?: number | null;
    }) =>
      apiFetch<ValidateFormulaResponse>(
        "/api/forecast/lines/validate-formula",
        {
          method: "POST",
          body: JSON.stringify(payload),
        },
      ),
  });
}
