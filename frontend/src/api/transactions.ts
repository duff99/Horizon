import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type { TransactionFilter, TransactionListResponse } from "../types/api";

export interface BulkCategorizeFilteredPayload {
  category_id: number;
  entity_id?: number;
  bank_account_id?: number;
  date_from?: string;
  date_to?: string;
  counterparty_id?: number;
  search?: string;
  uncategorized?: boolean;
  include_sepa_children?: boolean;
  amount_min?: number;
  amount_max?: number;
}

export async function fetchTransactions(
  filters: TransactionFilter = {},
): Promise<TransactionListResponse> {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v === undefined || v === null || v === "") return;
    params.set(k, String(v));
  });
  const url = `/api/transactions${params.toString() ? `?${params}` : ""}`;
  const resp = await fetch(url, { credentials: "include" });
  if (!resp.ok) throw new Error(`GET ${url} → ${resp.status}`);
  return resp.json();
}

export function useBulkCategorize() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (p: { transaction_ids: number[]; category_id: number }) =>
      apiFetch<{ updated_count: number }>("/api/transactions/bulk-categorize", {
        method: "POST", body: JSON.stringify(p),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["transactions"] }),
  });
}

export function bulkCategorizeFiltered(
  payload: BulkCategorizeFilteredPayload,
): Promise<{ updated_count: number }> {
  return apiFetch<{ updated_count: number }>("/api/transactions/bulk-categorize-filtered", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function useBulkCategorizeFiltered() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: bulkCategorizeFiltered,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["transactions"] }),
  });
}
