import { useState } from "react";
import { X } from "lucide-react";
import { Drawer as DrawerPrimitive } from "vaul";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { SortableRulesTable } from "@/components/SortableRulesTable";
import { RuleForm } from "@/components/RuleForm";
import {
  useRules,
  useCreateRule,
  useUpdateRule,
  useDeleteRule,
  useApplyRule,
  useReorderRules,
  type Rule,
  type RuleCreatePayload,
} from "@/api/rules";
import { useCategories } from "@/api/categories";
import { useEntities } from "@/api/entities";
import { useCounterparties } from "@/api/counterparties";
import { useBankAccounts } from "@/api/bankAccounts";
import { useMe } from "@/hooks/useAuth";
import { useEntityFilter } from "@/stores/entityFilter";
import { EntitySelector } from "@/components/EntitySelector";

export function RulesPage() {
  const meQuery = useMe();
  const entityId = useEntityFilter((s) => s.entityId);
  const rulesQuery = useRules({
    scope: "all",
    entity_id: entityId ?? undefined,
  });
  const categoriesQuery = useCategories();
  const entitiesQuery = useEntities();
  const counterpartiesQuery = useCounterparties({ entityId });
  const bankAccountsQuery = useBankAccounts();

  const createMut = useCreateRule();
  const updateMut = useUpdateRule();
  const deleteMut = useDeleteRule();
  const applyMut = useApplyRule();
  const reorderMut = useReorderRules();

  const [editing, setEditing] = useState<Rule | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const isLoading =
    rulesQuery.isLoading ||
    categoriesQuery.isLoading ||
    entitiesQuery.isLoading ||
    counterpartiesQuery.isLoading ||
    bankAccountsQuery.isLoading;

  const rules = rulesQuery.data ?? [];
  const categories = categoriesQuery.data ?? [];
  const entities = entitiesQuery.data ?? [];
  const counterparties = counterpartiesQuery.data ?? [];
  const bankAccounts = (bankAccountsQuery.data ?? []).map((ba) => ({
    id: ba.id,
    name: ba.name,
    entity_id: ba.entityId,
  }));

  async function handleSubmit(payload: RuleCreatePayload, applyAfter: boolean) {
    if (editing) {
      await updateMut.mutateAsync({ id: editing.id, patch: payload });
    } else {
      const created = await createMut.mutateAsync(payload);
      if (applyAfter) {
        await applyMut.mutateAsync(created.id);
      }
    }
    setDrawerOpen(false);
    setEditing(null);
  }

  const systemCount = rules.filter((r) => r.is_system).length;
  const customCount = rules.length - systemCount;

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight text-ink">
            Règles de catégorisation
          </h1>
          <p className="mt-0.5 text-[13px] text-muted-foreground">
            {rules.length} règle{rules.length > 1 ? "s" : ""}
            {systemCount > 0 && ` · ${systemCount} système · ${customCount} personnalisée${customCount > 1 ? "s" : ""}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <EntitySelector />
          <Button
            onClick={() => {
              setEditing(null);
              setDrawerOpen(true);
            }}
          >
            <svg
              aria-hidden
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              className="mr-1.5 h-3.5 w-3.5"
            >
              <path d="M5 12h14M12 5v14" />
            </svg>
            Nouvelle règle
          </Button>
        </div>
      </div>

      {/* Drawer custom direction=right (pattern HelpDrawer / BulkCategorizationDrawer).
          modal={false} + pas d'overlay, pour que les Popover Radix portés
          dans le body (CategoryCombobox dans RuleForm) restent cliquables. */}
      <DrawerPrimitive.Root
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        direction="right"
        modal={false}
        shouldScaleBackground={false}
      >
        <DrawerPrimitive.Portal>
          <DrawerPrimitive.Content
            aria-describedby={undefined}
            className={cn(
              "fixed inset-y-0 right-0 z-40 flex h-full w-full max-w-[640px] flex-col bg-panel shadow-xl outline-none",
              "border-l border-line-soft",
            )}
          >
            <header className="flex items-start justify-between gap-2 border-b border-line-soft px-5 py-4">
              <DrawerPrimitive.Title className="text-[15px] font-semibold text-ink">
                {editing ? "Modifier la règle" : "Nouvelle règle"}
              </DrawerPrimitive.Title>
              <button
                type="button"
                onClick={() => {
                  setDrawerOpen(false);
                  setEditing(null);
                }}
                aria-label="Fermer"
                className="rounded-md p-1.5 text-ink-2 hover:bg-panel-2 hover:text-ink"
              >
                <X className="h-4 w-4" aria-hidden />
              </button>
            </header>
            <div className="flex-1 overflow-y-auto p-6">
              <RuleForm
                categories={categories}
                entities={entities}
                counterparties={counterparties}
                bankAccounts={bankAccounts}
                initialValue={editing}
                onSubmit={handleSubmit}
                onCancel={() => {
                  setDrawerOpen(false);
                  setEditing(null);
                }}
              />
            </div>
          </DrawerPrimitive.Content>
        </DrawerPrimitive.Portal>
      </DrawerPrimitive.Root>

      {isLoading ? (
        <div className="rounded-xl border border-line-soft bg-panel p-10 text-center text-[13px] text-muted-foreground shadow-card">
          Chargement…
        </div>
      ) : (
        <SortableRulesTable
          rules={rules}
          categories={categories}
          onReorder={(items) => reorderMut.mutate(items)}
          onEdit={(r) => {
            setEditing(r);
            setDrawerOpen(true);
          }}
          onDelete={(r) => {
            if (confirm(`Supprimer la règle "${r.name}" ?`)) deleteMut.mutate(r.id);
          }}
          canDelete={meQuery.data?.role === "admin"}
        />
      )}
    </section>
  );
}
