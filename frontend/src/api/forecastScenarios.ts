import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type { Scenario, ScenarioCreate, ScenarioUpdate } from "@/types/forecast";

export function useScenarios(entityId: number | null | undefined) {
  return useQuery({
    queryKey: ["forecast-scenarios", entityId ?? null],
    queryFn: () => {
      const q = entityId != null ? `?entity_id=${entityId}` : "";
      return apiFetch<Scenario[]>(`/api/forecast/scenarios${q}`);
    },
    enabled: entityId != null,
  });
}

export function useCreateScenario() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ScenarioCreate) =>
      apiFetch<Scenario>("/api/forecast/scenarios", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["forecast-scenarios"] });
    },
  });
}

export function useUpdateScenario() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...patch }: { id: number } & ScenarioUpdate) =>
      apiFetch<Scenario>(`/api/forecast/scenarios/${id}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["forecast-scenarios"] });
    },
  });
}

export function useDeleteScenario() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch<void>(`/api/forecast/scenarios/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["forecast-scenarios"] });
    },
  });
}
