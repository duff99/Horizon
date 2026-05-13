import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";

export interface MonthBlock {
  month_label: string;
  in_cents: number;
  out_cents: number;
}

export interface MonthComparison {
  current: MonthBlock;
  previous: MonthBlock;
}

/**
 * Compare in/out d'un mois vs son mois précédent.
 * Si `month` (YYYY-MM) est fourni, le widget suit le sélecteur de période
 * du Dashboard ; sinon il s'ancre sur le mois courant.
 */
export function useMonthComparison(
  entityId: number | null,
  month?: string | null,
) {
  const params = new URLSearchParams();
  if (entityId != null) params.set("entity_id", String(entityId));
  if (month) params.set("month", month);
  return useQuery<MonthComparison>({
    queryKey: ["dashboard", "month-comparison", entityId, month ?? null],
    queryFn: () =>
      apiFetch<MonthComparison>(
        `/api/dashboard/month-comparison?${params.toString()}`,
      ),
    staleTime: 60_000,
  });
}
