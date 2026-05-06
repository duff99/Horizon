import { useQuery } from "@tanstack/react-query";
import type {
  Counterparty,
  CounterpartyWithAggregates,
  MergePreview,
} from "../types/api";

export type ListParams = {
  entityId?: number | null;
  includeIgnored?: boolean;
  search?: string;
};

export async function fetchCounterparties(
  args: ListParams = {},
): Promise<CounterpartyWithAggregates[]> {
  const params = new URLSearchParams();
  if (args.entityId != null) params.set("entity_id", String(args.entityId));
  if (args.includeIgnored) params.set("include_ignored", "true");
  if (args.search) params.set("search", args.search);
  const qs = params.toString() ? `?${params}` : "";
  const resp = await fetch(`/api/counterparties${qs}`, { credentials: "include" });
  if (!resp.ok) throw new Error(`GET /api/counterparties → ${resp.status}`);
  return resp.json();
}

export async function updateCounterparty(
  id: number,
  patch: { status?: "active" | "ignored"; name?: string },
): Promise<Counterparty> {
  const resp = await fetch(`/api/counterparties/${id}`, {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!resp.ok) throw new Error(`PATCH → ${resp.status}`);
  return resp.json();
}

export async function createCounterparty(payload: {
  entity_id: number;
  name: string;
}): Promise<Counterparty> {
  const resp = await fetch(`/api/counterparties`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    const txt = await resp.text();
    throw new Error(`POST /api/counterparties → ${resp.status} ${txt}`);
  }
  return resp.json();
}

export async function fetchMergePreview(
  sourceId: number,
  targetId: number,
): Promise<MergePreview> {
  const resp = await fetch(
    `/api/counterparties/${sourceId}/merge-preview?target_id=${targetId}`,
    { credentials: "include" },
  );
  if (!resp.ok) throw new Error(`merge-preview → ${resp.status}`);
  return resp.json();
}

export async function executeMerge(
  sourceId: number,
  targetId: number,
): Promise<void> {
  const resp = await fetch(`/api/counterparties/${sourceId}/merge`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target_id: targetId }),
  });
  if (!resp.ok) throw new Error(`merge → ${resp.status}`);
}

export function useCounterparties(filters: ListParams = {}) {
  return useQuery({
    queryKey: ["counterparties", filters],
    queryFn: () => fetchCounterparties(filters),
  });
}
