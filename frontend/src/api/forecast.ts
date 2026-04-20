import { apiFetch } from "./client";

export type ForecastRecurrence =
  | "NONE"
  | "WEEKLY"
  | "MONTHLY"
  | "QUARTERLY"
  | "YEARLY";

export interface ForecastEntry {
  id: number;
  entity_id: number;
  bank_account_id: number | null;
  label: string;
  amount: string;
  due_date: string;
  category_id: number | null;
  counterparty_id: number | null;
  recurrence: ForecastRecurrence;
  recurrence_until: string | null;
  notes: string | null;
}

export interface ForecastEntryCreate {
  entity_id: number;
  bank_account_id?: number | null;
  label: string;
  amount: string;
  due_date: string;
  category_id?: number | null;
  counterparty_id?: number | null;
  recurrence?: ForecastRecurrence;
  recurrence_until?: string | null;
  notes?: string | null;
}

export type ForecastEntryUpdate = Partial<Omit<ForecastEntryCreate, "entity_id">>;

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

export function listForecastEntries(entityId?: number): Promise<ForecastEntry[]> {
  const q = entityId ? `?entity_id=${entityId}` : "";
  return apiFetch<ForecastEntry[]>(`/api/forecast/entries${q}`);
}

export function createForecastEntry(
  input: ForecastEntryCreate,
): Promise<ForecastEntry> {
  return apiFetch<ForecastEntry>("/api/forecast/entries", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateForecastEntry(
  id: number,
  input: ForecastEntryUpdate,
): Promise<ForecastEntry> {
  return apiFetch<ForecastEntry>(`/api/forecast/entries/${id}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function deleteForecastEntry(id: number): Promise<void> {
  return apiFetch<void>(`/api/forecast/entries/${id}`, { method: "DELETE" });
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
