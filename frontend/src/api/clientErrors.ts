import { apiFetch } from "./client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

export interface ClientErrorItem {
  id: number;
  occurred_at: string;
  user_id: number | null;
  user_email: string | null;
  severity: string;
  source: string;
  message: string;
  stack: string | null;
  url: string | null;
  user_agent: string | null;
  request_id: string | null;
  context_json: Record<string, unknown> | null;
  acknowledged_at: string | null;
}

export interface ClientErrorListResponse {
  items: ClientErrorItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface ClientErrorFilters {
  severity?: string;
  acknowledged?: boolean;
  since?: string;
  until?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

export function fetchClientErrors(
  filters: ClientErrorFilters = {},
): Promise<ClientErrorListResponse> {
  const p = new URLSearchParams();
  if (filters.severity) p.set("severity", filters.severity);
  if (filters.acknowledged !== undefined)
    p.set("acknowledged", String(filters.acknowledged));
  if (filters.since) p.set("since", filters.since);
  if (filters.until) p.set("until", filters.until);
  if (filters.search) p.set("search", filters.search);
  if (filters.limit != null) p.set("limit", String(filters.limit));
  if (filters.offset != null) p.set("offset", String(filters.offset));
  const qs = p.toString();
  return apiFetch<ClientErrorListResponse>(
    `/api/admin/client-errors${qs ? `?${qs}` : ""}`,
  );
}

export function useClientErrors(filters: ClientErrorFilters = {}) {
  return useQuery({
    queryKey: ["admin", "client-errors", filters],
    queryFn: () => fetchClientErrors(filters),
  });
}

export function useAcknowledgeClientError() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch<{ id: number; acknowledged_at: string }>(
        `/api/admin/client-errors/${id}/acknowledge`,
        { method: "PATCH" },
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["admin", "client-errors"] }),
  });
}
