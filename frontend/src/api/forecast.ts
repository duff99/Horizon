import { apiFetch } from "./client";

export type ForecastRecurrence =
  | "NONE"
  | "WEEKLY"
  | "MONTHLY"
  | "QUARTERLY"
  | "YEARLY";

export interface ForecastProjectionPoint {
  date: string;
  balance: string;
  planned_net: string;
}

export interface ForecastProjection {
  starting_balance: string;
  starting_date: string;
  horizon_days: number;
  points: ForecastProjectionPoint[];
}

export interface DetectedRecurrenceSuggestion {
  counterparty_id: number | null;
  counterparty_name: string;
  average_amount: string;
  last_occurrence: string;
  next_expected: string;
  recurrence: ForecastRecurrence;
  occurrences_count: number;
  entity_id: number;
}

export function fetchForecastProjection(args: {
  horizonDays: number;
  entityId?: number;
}): Promise<ForecastProjection> {
  const params = new URLSearchParams({ horizon_days: String(args.horizonDays) });
  if (args.entityId !== undefined) params.set("entity_id", String(args.entityId));
  return apiFetch<ForecastProjection>(`/api/forecast/projection?${params}`);
}

export function fetchRecurringSuggestions(
  entityId: number,
): Promise<DetectedRecurrenceSuggestion[]> {
  return apiFetch<DetectedRecurrenceSuggestion[]>(
    `/api/forecast/recurring-suggestions?entity_id=${entityId}`,
  );
}
