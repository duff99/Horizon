import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchTransactions, useBulkCategorize } from "../api/transactions";
import { TransactionFilters } from "../components/TransactionFilters";
import { CategoryCombobox } from "../components/CategoryCombobox";
import { RuleForm } from "../components/RuleForm";
import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer";
import { Button } from "@/components/ui/button";
import { useCategories } from "@/api/categories";
import { useEntities } from "@/api/entities";
import { useCounterparties } from "@/api/counterparties";
import { useBankAccounts } from "@/api/bankAccounts";
import {
  suggestRuleFromTransactions,
  useCreateRule,
  useApplyRule,
  type RuleCreatePayload,
  type RuleSuggestion,
} from "@/api/rules";
import type { TransactionFilter } from "../types/api";

const EUR = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 2,
});

export function TransactionsPage() {
  const [filters, setFilters] = useState<TransactionFilter>({ page: 1, per_page: 50 });
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [bulkCategoryId, setBulkCategoryId] = useState<number | null>(null);
  const [ruleDrawerOpen, setRuleDrawerOpen] = useState(false);
  const [ruleInitialValue, setRuleInitialValue] = useState<RuleSuggestion | null>(null);
  const [suggestError, setSuggestError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["transactions", filters],
    queryFn: () => fetchTransactions(filters),
  });

  const categoriesQuery = useCategories();
  const entitiesQuery = useEntities();
  const counterpartiesQuery = useCounterparties({});
  const bankAccountsQuery = useBankAccounts();

  const bulkMut = useBulkCategorize();
  const createRuleMut = useCreateRule();
  const applyRuleMut = useApplyRule();

  const categories = categoriesQuery.data ?? [];
  const entities = entitiesQuery.data ?? [];
  const counterparties = counterpartiesQuery.data ?? [];
  const bankAccounts = (bankAccountsQuery.data ?? []).map((ba) => ({
    id: ba.id,
    name: ba.name,
    entity_id: ba.entityId,
  }));

  const items = data?.items ?? [];
  const allPageIds = items.map((tx) => tx.id);
  const allSelected = allPageIds.length > 0 && allPageIds.every((id) => selectedIds.has(id));

  function toggleSelectAll() {
    if (allSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(allPageIds));
    }
  }

  function toggleRow(id: number) {
    const next = new Set(selectedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelectedIds(next);
  }

  function handleUncategorizedChange(checked: boolean) {
    setFilters({ ...filters, uncategorized: checked || undefined, page: 1 });
    setSelectedIds(new Set());
  }

  async function handleBulkCategorize() {
    if (!bulkCategoryId) return;
    await bulkMut.mutateAsync({ transaction_ids: [...selectedIds], category_id: bulkCategoryId });
    setSelectedIds(new Set());
    setBulkCategoryId(null);
  }

  async function handleSuggestRule() {
    setSuggestError(null);
    try {
      const suggestion = await suggestRuleFromTransactions([...selectedIds]);
      setRuleInitialValue(suggestion);
      setRuleDrawerOpen(true);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setSuggestError(msg);
    }
  }

  async function handleRuleSubmit(payload: RuleCreatePayload, applyAfter: boolean) {
    const created = await createRuleMut.mutateAsync(payload);
    if (applyAfter) {
      await applyRuleMut.mutateAsync(created.id);
    }
    setRuleDrawerOpen(false);
    setRuleInitialValue(null);
    setSelectedIds(new Set());
    setBulkCategoryId(null);
  }

  const ruleFormInitialValue = ruleInitialValue
    ? {
        id: 0,
        name: "",
        entity_id: null,
        priority: 5000,
        is_system: false,
        label_operator: ruleInitialValue.suggested_label_operator,
        label_value: ruleInitialValue.suggested_label_value,
        direction: ruleInitialValue.suggested_direction,
        amount_operator: null,
        amount_value: null,
        amount_value2: null,
        counterparty_id: null,
        bank_account_id: ruleInitialValue.suggested_bank_account_id,
        category_id: bulkCategoryId ?? 0,
        created_at: "",
        updated_at: "",
      }
    : null;

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-6">
      <h1 className="text-2xl font-semibold">Transactions</h1>
      <TransactionFilters value={filters} onChange={setFilters} />

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={!!filters.uncategorized}
          onChange={(e) => handleUncategorizedChange(e.target.checked)}
        />
        Afficher uniquement les non catégorisées
      </label>

      {selectedIds.size > 0 && (
        <div className="sticky top-0 z-10 bg-background border-b p-3 flex flex-wrap gap-2 items-center">
          <span className="text-sm">
            {selectedIds.size} transaction{selectedIds.size > 1 ? "s" : ""} sélectionnée{selectedIds.size > 1 ? "s" : ""}
          </span>
          <div className="w-56">
            <CategoryCombobox
              categories={categories}
              value={bulkCategoryId}
              onChange={setBulkCategoryId}
            />
          </div>
          <Button
            disabled={!bulkCategoryId || bulkMut.isPending}
            onClick={handleBulkCategorize}
          >
            Catégoriser {selectedIds.size} transaction{selectedIds.size > 1 ? "s" : ""}
          </Button>
          <Button variant="outline" onClick={handleSuggestRule}>
            Créer une règle depuis la sélection
          </Button>
          {suggestError && (
            <span className="text-destructive text-sm">{suggestError}</span>
          )}
        </div>
      )}

      {isLoading && <p>Chargement…</p>}

      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left">
            <th className="py-2 pr-2 w-8">
              <input
                type="checkbox"
                aria-label="Tout sélectionner"
                checked={allSelected}
                onChange={toggleSelectAll}
              />
            </th>
            <th className="py-2">Date</th>
            <th>Libellé</th>
            <th>Contrepartie</th>
            <th>Catégorie</th>
            <th className="text-right">Montant</th>
          </tr>
        </thead>
        <tbody>
          {items.map((tx) => (
            <tr
              key={tx.id}
              className={`border-b ${tx.is_aggregation_parent ? "bg-muted/30 font-medium" : ""}`}
            >
              <td className="py-2 pr-2">
                <input
                  type="checkbox"
                  aria-label={`Sélectionner transaction ${tx.id}`}
                  checked={selectedIds.has(tx.id)}
                  onChange={() => toggleRow(tx.id)}
                />
              </td>
              <td className="py-2">
                {new Date(tx.operation_date).toLocaleDateString("fr-FR")}
              </td>
              <td>{tx.label}</td>
              <td>{tx.counterparty?.name ?? "—"}</td>
              <td>{tx.category?.name ?? "Non catégorisée"}</td>
              <td className={`text-right ${parseFloat(tx.amount) < 0 ? "text-destructive" : "text-emerald-700"}`}>
                {EUR.format(parseFloat(tx.amount))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {data && (
        <div className="flex items-center justify-between text-sm">
          <span>
            {data.total} transaction(s) — page {data.page}
          </span>
          <div className="flex gap-2">
            <button
              disabled={data.page <= 1}
              onClick={() => setFilters({ ...filters, page: data.page - 1 })}
              className="rounded-md border px-3 py-1 disabled:opacity-40"
            >
              Précédent
            </button>
            <button
              disabled={data.page * data.per_page >= data.total}
              onClick={() => setFilters({ ...filters, page: data.page + 1 })}
              className="rounded-md border px-3 py-1 disabled:opacity-40"
            >
              Suivant
            </button>
          </div>
        </div>
      )}

      <Drawer open={ruleDrawerOpen} onOpenChange={setRuleDrawerOpen}>
        <DrawerContent>
          <DrawerHeader>
            <DrawerTitle>Nouvelle règle depuis la sélection</DrawerTitle>
          </DrawerHeader>
          <div className="p-6 max-w-2xl">
            <RuleForm
              categories={categories}
              entities={entities}
              counterparties={counterparties}
              bankAccounts={bankAccounts}
              initialValue={ruleFormInitialValue}
              onSubmit={handleRuleSubmit}
              onCancel={() => {
                setRuleDrawerOpen(false);
                setRuleInitialValue(null);
              }}
            />
          </div>
        </DrawerContent>
      </Drawer>
    </div>
  );
}
