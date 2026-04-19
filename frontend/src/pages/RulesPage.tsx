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

  if (
    rulesQuery.isLoading ||
    categoriesQuery.isLoading ||
    entitiesQuery.isLoading ||
    counterpartiesQuery.isLoading ||
    bankAccountsQuery.isLoading
  ) {
    return null;
  }

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

  return (
    <section className="p-6">
      <header className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-semibold">Règles de catégorisation</h1>
        <Drawer open={drawerOpen} onOpenChange={setDrawerOpen}>
          <DrawerTrigger asChild>
            <Button onClick={() => setEditing(null)}>Nouvelle règle</Button>
          </DrawerTrigger>
          <DrawerContent>
            <DrawerHeader>
              <DrawerTitle>
                {editing ? "Modifier la règle" : "Nouvelle règle"}
              </DrawerTitle>
            </DrawerHeader>
            <div className="p-6 max-w-2xl">
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
      </header>

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
    </section>
  );
}
