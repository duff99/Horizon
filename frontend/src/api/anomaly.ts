/**
 * Clients fetch + hooks TanStack Query pour /api/analysis/anomalies (G4).
 */
import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "./client";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AnomalyRow {
  transaction_id: number;
  operation_date: string; // "YYYY-MM-DD"
  label: string;
  amount_cents: number;
  category_id: number | null;
  category_label: string | null;
  p95_cents: number;
  ratio: number;
}

export interface AnomalyResponse {
  entity_id: number;
  days_analyzed: number;
  anomaly_count: number;
  rows: AnomalyRow[];
}

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

export function fetchAnomalies(args: {
  entityId?: number;
  days?: number;
}): Promise<AnomalyResponse> {
  return apiFetch<AnomalyResponse>(
    `/api/analysis/anomalies${buildParams([
      ["entity_id", args.entityId],
      ["days", args.days],
    ])}`,
  );
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useAnomalies(args: { entityId?: number; days?: number }) {
  return useQuery({
    queryKey: ["analysis", "anomalies", args.entityId, args.days],
    queryFn: () => fetchAnomalies(args),
    staleTime: 5 * 60_000,
    enabled: args.entityId !== undefined,
  });
}
