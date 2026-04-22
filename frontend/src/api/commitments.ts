import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";

export type CommitmentStatus = "pending" | "paid" | "cancelled";
export type CommitmentDirection = "in" | "out";

export interface Commitment {
  id: number;
  entity_id: number;
  counterparty_id: number | null;
  counterparty_name: string | null;
  category_id: number | null;
  category_name: string | null;
  bank_account_id: number | null;
  direction: CommitmentDirection;
  amount_cents: number;
  issue_date: string;
  expected_date: string;
  status: CommitmentStatus;
  matched_transaction_id: number | null;
  reference: string | null;
  description: string | null;
  pdf_attachment_id: number | null;
  created_by_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface CommitmentCreate {
  entity_id: number;
  counterparty_id?: number | null;
  category_id?: number | null;
  bank_account_id?: number | null;
  direction: CommitmentDirection;
  amount_cents: number;
  issue_date: string;
  expected_date: string;
  reference?: string | null;
  description?: string | null;
  pdf_attachment_id?: number | null;
}

export interface CommitmentUpdate {
  counterparty_id?: number | null;
  category_id?: number | null;
  bank_account_id?: number | null;
  direction?: CommitmentDirection | null;
  amount_cents?: number | null;
  issue_date?: string | null;
  expected_date?: string | null;
  status?: CommitmentStatus | null;
  reference?: string | null;
  description?: string | null;
  pdf_attachment_id?: number | null;
}

export interface CommitmentListResponse {
  items: Commitment[];
  total: number;
  page: number;
  per_page: number;
}

export interface CommitmentTransactionBrief {
  id: number;
  operation_date: string;
  label: string;
  amount: string;
  bank_account_label: string | null;
}

export interface CommitmentSuggestionResponse {
  candidates: CommitmentTransactionBrief[];
}

export interface CommitmentsFilters {
  entityId?: number | null;
  status?: CommitmentStatus;
  direction?: CommitmentDirection;
  from?: string;
  to?: string;
  page?: number;
  perPage?: number;
}

function buildQuery(filters: CommitmentsFilters): string {
  const params = new URLSearchParams();
  if (filters.entityId != null) params.set("entity_id", String(filters.entityId));
  if (filters.status) params.set("status", filters.status);
  if (filters.direction) params.set("direction", filters.direction);
  if (filters.from) params.set("from", filters.from);
  if (filters.to) params.set("to", filters.to);
  if (filters.page) params.set("page", String(filters.page));
  if (filters.perPage) params.set("per_page", String(filters.perPage));
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export function useCommitments(filters: CommitmentsFilters = {}) {
  return useQuery({
    queryKey: ["commitments", filters],
    queryFn: () =>
      apiFetch<CommitmentListResponse>(`/api/commitments${buildQuery(filters)}`),
  });
}

export function useCommitment(id: number | null) {
  return useQuery({
    queryKey: ["commitment", id],
    queryFn: () => apiFetch<Commitment>(`/api/commitments/${id}`),
    enabled: id != null,
  });
}

export function useCreateCommitment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CommitmentCreate) =>
      apiFetch<Commitment>("/api/commitments", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["commitments"] });
    },
  });
}

export function useUpdateCommitment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...patch }: { id: number } & CommitmentUpdate) =>
      apiFetch<Commitment>(`/api/commitments/${id}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
      }),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["commitments"] });
      qc.invalidateQueries({ queryKey: ["commitment", vars.id] });
    },
  });
}

export function useCancelCommitment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch<void>(`/api/commitments/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["commitments"] });
    },
  });
}

export function useMatchCommitment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, transaction_id }: { id: number; transaction_id: number }) =>
      apiFetch<Commitment>(`/api/commitments/${id}/match`, {
        method: "POST",
        body: JSON.stringify({ transaction_id }),
      }),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["commitments"] });
      qc.invalidateQueries({ queryKey: ["commitment", vars.id] });
    },
  });
}

export function useUnmatchCommitment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch<Commitment>(`/api/commitments/${id}/unmatch`, {
        method: "POST",
      }),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["commitments"] });
      qc.invalidateQueries({ queryKey: ["commitment", id] });
    },
  });
}

export function useSuggestMatches(id: number | null) {
  return useQuery({
    queryKey: ["commitment-suggestions", id],
    queryFn: () =>
      apiFetch<CommitmentSuggestionResponse>(
        `/api/commitments/${id}/suggest-matches`,
      ),
    enabled: id != null,
  });
}
