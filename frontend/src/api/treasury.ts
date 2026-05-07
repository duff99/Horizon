/**
 * Clients fetch + hooks TanStack Query pour `/api/treasury/*` (G1, G10).
 */
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "./client";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface DailyBalancePoint {
  date: string;         // "YYYY-MM-DD"
  balance: string;      // Decimal sérialisé en string par Pydantic
}

export interface DailyBalanceResponse {
  entity_id: number;
  days: number;
  points: DailyBalancePoint[];
  latest_balance: string | null;
  latest_date: string | null;
}

export interface PerAccountBalance {
  account_id: number;
  account_name: string;
  bank_name: string;
  iban_last4: string;
  balance_cents: number;
  balance_30d_ago_cents: number | null;
  variation_30d_cents: number | null;
  last_import_date: string | null;
  sparkline: number[];
}

export interface PerAccountBalanceResponse {
  entity_id: number | null;
  accounts: PerAccountBalance[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function buildParams(
  entries: Array<[string, string | number | undefined | null]>,
): string {
  const p = new URLSearchParams();
  for (const [k, v] of entries) {
    if (v === undefined || v === null) continue;
    p.set(k, String(v));
  }
  const s = p.toString();
  return s ? `?${s}` : "";
}

// ---------------------------------------------------------------------------
// G1 — Solde quotidien 90 jours
// ---------------------------------------------------------------------------

export function fetchDailyBalance(args: {
  entityId: number;
  days?: number;
}): Promise<DailyBalanceResponse> {
  return apiFetch<DailyBalanceResponse>(
    `/api/treasury/daily-balance${buildParams([
      ["entity_id", args.entityId],
      ["days", args.days ?? 90],
    ])}`,
  );
}

export function useDailyBalance(args: {
  entityId: number | undefined;
  days?: number;
}) {
  return useQuery({
    queryKey: ["treasury-daily-balance", args.entityId, args.days ?? 90],
    queryFn: () =>
      fetchDailyBalance({ entityId: args.entityId!, days: args.days }),
    enabled: args.entityId !== undefined,
    staleTime: 120_000,
  });
}

// ---------------------------------------------------------------------------
// G10 — Position par compte bancaire
// ---------------------------------------------------------------------------

export function fetchPerAccount(args: {
  entityId?: number;
}): Promise<PerAccountBalanceResponse> {
  return apiFetch<PerAccountBalanceResponse>(
    `/api/treasury/per-account${buildParams([["entity_id", args.entityId]])}`,
  );
}

export function usePerAccount(args: { entityId: number | undefined }) {
  return useQuery({
    queryKey: ["treasury-per-account", args.entityId],
    queryFn: () => fetchPerAccount({ entityId: args.entityId }),
    enabled: args.entityId !== undefined,
    staleTime: 120_000,
  });
}

// ---------------------------------------------------------------------------
// G2 — Rolling 13-week
// ---------------------------------------------------------------------------

export interface Rolling13WPoint {
  week_label: string;      // "2026-W18"
  week_start: string;      // "YYYY-MM-DD" (lundi de la semaine)
  realized_cents: number;
  forecast_cents: number;
  is_past: boolean;
}

export interface Rolling13WResponse {
  entity_id: number;
  scenario_id: number | null;
  points: Rolling13WPoint[];
}

export function fetchRolling13W(args: {
  entityId: number;
  scenarioId?: number | null;
}): Promise<Rolling13WResponse> {
  return apiFetch<Rolling13WResponse>(
    `/api/forecast/rolling-13w${buildParams([
      ["entity_id", args.entityId],
      ["scenario_id", args.scenarioId ?? undefined],
    ])}`,
  );
}

export function useRolling13W(args: {
  entityId: number | null | undefined;
  scenarioId?: number | null;
}) {
  return useQuery({
    queryKey: ["rolling-13w", args.entityId, args.scenarioId ?? null],
    queryFn: () =>
      fetchRolling13W({
        entityId: args.entityId!,
        scenarioId: args.scenarioId,
      }),
    enabled: args.entityId != null,
    staleTime: 120_000,
  });
}
