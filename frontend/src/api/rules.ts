import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";

export type RuleLabelOperator = "CONTAINS" | "STARTS_WITH" | "ENDS_WITH" | "EQUALS";
export type RuleAmountOperator = "EQ" | "NE" | "GT" | "LT" | "BETWEEN";
export type RuleDirection = "CREDIT" | "DEBIT" | "ANY";

export interface Rule {
  id: number;
  name: string;
  entity_id: number | null;
  priority: number;
  is_system: boolean;
  label_operator: RuleLabelOperator | null;
  label_value: string | null;
  direction: RuleDirection;
  amount_operator: RuleAmountOperator | null;
  amount_value: string | null;
  amount_value2: string | null;
  counterparty_id: number | null;
  bank_account_id: number | null;
  category_id: number;
  created_at: string;
  updated_at: string;
}

export interface RuleCreatePayload {
  name: string;
  entity_id?: number | null;
  priority: number;
  label_operator?: RuleLabelOperator | null;
  label_value?: string | null;
  direction: RuleDirection;
  amount_operator?: RuleAmountOperator | null;
  amount_value?: string | null;
  amount_value2?: string | null;
  counterparty_id?: number | null;
  bank_account_id?: number | null;
  category_id: number;
}

export interface RulePreviewResponse {
  matching_count: number;
  sample: Array<{
    id: number;
    operation_date: string;
    amount: string;
    label: string;
    current_category_id: number | null;
  }>;
}

export interface RuleSuggestion {
  suggested_label_operator: "CONTAINS" | "STARTS_WITH";
  suggested_label_value: string;
  suggested_direction: RuleDirection;
  suggested_bank_account_id: number | null;
  transaction_count: number;
}

export const rulesKey = (scope?: string, entityId?: number) =>
  ["rules", scope ?? "all", entityId ?? null] as const;

export function useRules(params: { scope?: string; entity_id?: number }) {
  const qs = new URLSearchParams();
  if (params.scope) qs.set("scope", params.scope);
  if (params.entity_id != null) qs.set("entity_id", String(params.entity_id));
  return useQuery({
    queryKey: rulesKey(params.scope, params.entity_id),
    queryFn: () => apiFetch<Rule[]>(`/api/rules?${qs}`),
  });
}

export function useCreateRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (p: RuleCreatePayload) =>
      apiFetch<Rule>("/api/rules", { method: "POST", body: JSON.stringify(p) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  });
}

export function useUpdateRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { id: number; patch: Partial<RuleCreatePayload> }) =>
      apiFetch<Rule>(`/api/rules/${input.id}`, {
        method: "PATCH", body: JSON.stringify(input.patch),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  });
}

export function useDeleteRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch<void>(`/api/rules/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  });
}

export function previewRule(p: RuleCreatePayload): Promise<RulePreviewResponse> {
  return apiFetch<RulePreviewResponse>("/api/rules/preview", {
    method: "POST", body: JSON.stringify(p),
  });
}

export function useApplyRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch<{ updated_count: number }>(`/api/rules/${id}/apply`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["rules"] });
      qc.invalidateQueries({ queryKey: ["transactions"] });
    },
  });
}

export function useReorderRules() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (items: Array<{ id: number; priority: number }>) =>
      apiFetch<Rule[]>("/api/rules/reorder", {
        method: "POST", body: JSON.stringify(items),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  });
}

export function suggestRuleFromTransactions(
  transaction_ids: number[],
): Promise<RuleSuggestion> {
  return apiFetch<RuleSuggestion>("/api/rules/from-transactions", {
    method: "POST", body: JSON.stringify({ transaction_ids }),
  });
}
