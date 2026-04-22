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

export function useMonthComparison(entityId: number | null) {
  const params = new URLSearchParams();
  if (entityId != null) params.set("entity_id", String(entityId));
  return useQuery<MonthComparison>({
    queryKey: ["dashboard", "month-comparison", entityId],
    queryFn: () =>
      apiFetch<MonthComparison>(
        `/api/dashboard/month-comparison?${params.toString()}`,
      ),
    staleTime: 60_000,
  });
}
