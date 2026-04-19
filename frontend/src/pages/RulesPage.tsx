import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "@/components/ui/drawer";
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

export function RulesPage() {
  const meQuery = useMe();
  const rulesQuery = useRules({ scope: "all" });
  const categoriesQuery = useCategories();
  const entitiesQuery = useEntities();
  const counterpartiesQuery = useCounterparties({});
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight text-ink">
            Règles de catégorisation
          </h1>
          <p className="mt-0.5 text-[13px] text-muted-foreground">
            {rules.length} règle{rules.length > 1 ? "s" : ""}
            {systemCount > 0 && ` · ${systemCount} système · ${customCount} personnalisée${customCount > 1 ? "s" : ""}`}
          </p>
        </div>
        <Drawer open={drawerOpen} onOpenChange={setDrawerOpen}>
          <DrawerTrigger asChild>
            <Button onClick={() => setEditing(null)}>
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
          </DrawerTrigger>
          <DrawerContent>
            <DrawerHeader>
              <DrawerTitle>
                {editing ? "Modifier la règle" : "Nouvelle règle"}
              </DrawerTitle>
            </DrawerHeader>
            <div className="max-w-2xl p-6">
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
          </DrawerContent>
        </Drawer>
      </div>

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
