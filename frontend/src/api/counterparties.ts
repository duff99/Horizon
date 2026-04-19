import { useQuery } from "@tanstack/react-query";
import type { Counterparty } from "../types/api";

export async function fetchCounterparties(
  status?: "pending" | "active" | "ignored",
): Promise<Counterparty[]> {
  const qs = status ? `?status=${status}` : "";
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

export function useCounterparties(filters: { status?: "pending" | "active" | "ignored" } = {}) {
  return useQuery({
    queryKey: ["counterparties", filters],
    queryFn: () => fetchCounterparties(filters.status),
  });
}
