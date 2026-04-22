import { useQuery } from "@tanstack/react-query";
import type { Counterparty } from "../types/api";

export async function fetchCounterparties(
  args: {
    status?: "pending" | "active" | "ignored";
    entityId?: number | null;
  } = {},
): Promise<Counterparty[]> {
  const params = new URLSearchParams();
  if (args.status) params.set("status", args.status);
  if (args.entityId != null) params.set("entity_id", String(args.entityId));
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

export function useCounterparties(
  filters: {
    status?: "pending" | "active" | "ignored";
    entityId?: number | null;
  } = {},
) {
  return useQuery({
    queryKey: ["counterparties", filters],
    queryFn: () => fetchCounterparties(filters),
  });
}
