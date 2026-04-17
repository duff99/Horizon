import type { TransactionFilter, TransactionListResponse } from "../types/api";

export async function fetchTransactions(
  filters: TransactionFilter = {},
): Promise<TransactionListResponse> {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") params.set(k, String(v));
  });
  const url = `/api/transactions${params.toString() ? `?${params}` : ""}`;
  const resp = await fetch(url, { credentials: "include" });
  if (!resp.ok) throw new Error(`GET ${url} → ${resp.status}`);
  return resp.json();
}
