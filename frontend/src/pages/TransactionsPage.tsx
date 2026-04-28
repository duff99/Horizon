import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchTransactions, useBulkCategorize } from "../api/transactions";
import { useEntityFilter } from "../stores/entityFilter";
import { EntitySelector } from "@/components/EntitySelector";
import { TransactionFilters } from "../components/TransactionFilters";
import { CategoryCombobox } from "../components/CategoryCombobox";
import { Pagination, type PageSize } from "@/components/Pagination";
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
import { cn } from "@/lib/utils";

const EUR = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 2,
});

const DATE = new Intl.DateTimeFormat("fr-FR", {
  day: "2-digit",
  month: "short",
});

export function TransactionsPage() {
  const [filters, setFilters] = useState<TransactionFilter>({ page: 1, per_page: 50 });
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [bulkCategoryId, setBulkCategoryId] = useState<number | null>(null);
  const [ruleDrawerOpen, setRuleDrawerOpen] = useState(false);
  const [ruleInitialValue, setRuleInitialValue] = useState<RuleSuggestion | null>(null);
  const [suggestError, setSuggestError] = useState<string | null>(null);

  const entityId = useEntityFilter((s) => s.entityId);

  const queryFilters: TransactionFilter = {
    ...filters,
    entity_id: entityId ?? undefined,
  };

  const { data, isLoading } = useQuery({
    queryKey: ["transactions", queryFilters],
    queryFn: () => fetchTransactions(queryFilters),
  });

  const categoriesQuery = useCategories();
  const entitiesQuery = useEntities();
  const counterpartiesQuery = useCounterparties({ entityId });
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

  const uncategorizedCount = items.filter((tx) => !tx.category).length;
  const totalCount = data?.total ?? 0;

  return (
    <div className="space-y-6">
      {/* Page head */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight text-ink">Transactions</h1>
          <p className="mt-0.5 text-[13px] text-muted-foreground">
            {totalCount.toLocaleString("fr-FR")} opération{totalCount > 1 ? "s" : ""}
            {filters.uncategorized
              ? " · filtre : non catégorisées"
              : uncategorizedCount > 0
              ? ` · ${uncategorizedCount} non catégorisée${uncategorizedCount > 1 ? "s" : ""} sur cette page`
              : ""}
          </p>
        </div>
        <EntitySelector />
      </div>

      {/* Card: filters + bulk + table */}
      <div className="overflow-hidden rounded-xl border border-line-soft bg-panel shadow-card">
        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2 border-b border-line-soft bg-panel-2 px-5 py-3">
          <TransactionFilters value={filters} onChange={setFilters} />
          <label
            className={cn(
              "ml-auto flex cursor-pointer items-center gap-2 rounded-md border px-2.5 py-1.5 text-[12.5px] transition-colors",
              filters.uncategorized
                ? "border-ink bg-ink text-white"
                : "border-line bg-panel text-ink-2 hover:border-ink-2",
            )}
          >
            <input
              type="checkbox"
              className="h-3.5 w-3.5 accent-accent"
              checked={!!filters.uncategorized}
              onChange={(e) => handleUncategorizedChange(e.target.checked)}
            />
            Non catégorisées uniquement
          </label>
        </div>

        {/* Bulk toolbar */}
        {selectedIds.size > 0 && (
          <div className="flex flex-wrap items-center gap-2 border-b border-emerald-200 bg-emerald-50 px-5 py-2.5 text-[13px]">
            <span className="font-semibold text-emerald-800">
              {selectedIds.size} sélectionnée{selectedIds.size > 1 ? "s" : ""}
            </span>
            <div className="flex-1" />
            <div className="w-56">
              <CategoryCombobox
                categories={categories}
                value={bulkCategoryId}
                onChange={setBulkCategoryId}
              />
            </div>
            <Button
              size="sm"
              disabled={!bulkCategoryId || bulkMut.isPending}
              onClick={handleBulkCategorize}
            >
              Catégoriser
            </Button>
            <Button size="sm" variant="outline" onClick={handleSuggestRule}>
              Suggérer une règle
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setSelectedIds(new Set())}>
              Désélectionner
            </Button>
            {suggestError && (
              <span className="w-full text-[12.5px] text-debit">{suggestError}</span>
            )}
          </div>
        )}

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-line-soft bg-panel-2">
                <th className="w-[38px] px-5 py-2.5">
                  <input
                    type="checkbox"
                    aria-label="Tout sélectionner"
                    checked={allSelected}
                    onChange={toggleSelectAll}
                    className="h-3.5 w-3.5 accent-accent"
                  />
                </th>
                <th className="px-2 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Date
                </th>
                {entityId === null && (
                  <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Société
                  </th>
                )}
                <th className="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Tiers / Libellé
                </th>
                <th className="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Catégorie
                </th>
                <th className="sticky right-0 min-w-[130px] bg-panel-2 px-5 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Montant
                </th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={entityId === null ? 6 : 5} className="px-5 py-10 text-center text-[13px] text-muted-foreground">
                    Chargement…
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={entityId === null ? 6 : 5} className="px-5 py-10 text-center text-[13px] text-muted-foreground">
                    Aucune transaction.
                  </td>
                </tr>
              ) : (
                items.map((tx) => {
                  const amount = parseFloat(tx.amount);
                  const selected = selectedIds.has(tx.id);
                  return (
                    <tr
                      key={tx.id}
                      className={cn(
                        "border-b border-line-soft transition-colors hover:bg-panel-2",
                        selected && "bg-teal-50/60 hover:bg-teal-50",
                        tx.is_aggregation_parent && "bg-panel-2 font-medium",
                      )}
                    >
                      <td className="w-[38px] px-5 py-2.5">
                        <input
                          type="checkbox"
                          aria-label={`Sélectionner transaction ${tx.id}`}
                          checked={selected}
                          onChange={() => toggleRow(tx.id)}
                          className="h-3.5 w-3.5 accent-accent"
                        />
                      </td>
                      <td className="whitespace-nowrap px-2 py-2.5 text-[12.5px] text-muted-foreground mono">
                        {DATE.format(new Date(tx.operation_date))}
                      </td>
                      {entityId === null && (
                        <td className="whitespace-nowrap px-3 py-2.5 text-[12.5px] text-ink-2">
                          {tx.entity_name}
                        </td>
                      )}
                      <td className="max-w-[380px] px-4 py-2.5 text-[13.5px]">
                        <div className="truncate font-medium text-ink" title={tx.counterparty?.name ?? tx.label}>
                          {tx.counterparty?.name ?? tx.label}
                        </div>
                        {tx.counterparty?.name && (
                          <div className="mt-0.5 truncate text-[12px] text-muted-foreground" title={tx.label}>
                            {tx.label}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-2.5 text-[13px]">
                        {tx.category ? (
                          <span className="inline-flex items-center gap-1.5 rounded-md border border-line-soft bg-panel-2 px-2 py-0.5 text-[12px] font-medium text-ink-2">
                            <span className="h-2 w-2 rounded-sm bg-slate-400" />
                            {tx.category.name}
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 rounded-md border border-amber-200 bg-amber-50 px-2 py-0.5 text-[12px] font-medium text-amber-800">
                            ⚠ Non catégorisée
                          </span>
                        )}
                      </td>
                      <td
                        className={cn(
                          "sticky right-0 min-w-[130px] whitespace-nowrap bg-panel px-5 py-2.5 text-right font-semibold mono",
                          selected && "bg-teal-50/60",
                          tx.is_aggregation_parent && "bg-panel-2",
                          amount < 0 ? "text-debit" : "text-credit",
                        )}
                      >
                        {amount >= 0 ? "+" : ""}
                        {EUR.format(amount)}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Footer / pagination — composant Pagination réutilisable */}
        {data && data.total > 0 && (
          <Pagination
            page={data.page}
            perPage={data.per_page}
            total={data.total}
            onPageChange={(p) => setFilters({ ...filters, page: p })}
            onPerPageChange={(per) =>
              setFilters({ ...filters, per_page: per as PageSize, page: 1 })
            }
          />
        )}
      </div>

      <Drawer open={ruleDrawerOpen} onOpenChange={setRuleDrawerOpen}>
        <DrawerContent>
          <DrawerHeader>
            <DrawerTitle>Nouvelle règle depuis la sélection</DrawerTitle>
          </DrawerHeader>
          <div className="max-w-2xl p-6">
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
