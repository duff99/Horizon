import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useCommitments } from "@/api/commitments";
import { useLines } from "@/api/forecastLines";
import { fetchTransactions } from "@/api/transactions";
import { useCategories } from "@/api/categories";
import { MethodForm } from "./MethodForm";
import {
  firstDayOfMonth,
  formatCents,
  formatMonthLabel,
  lastDayOfMonth,
} from "@/lib/forecastFormat";
import { cn } from "@/lib/utils";

type Tab = "paid" | "committed" | "forecast";

interface Props {
  open: boolean;
  month: string;
  categoryId: number;
  entityId: number;
  scenarioId: number;
  accountIds: number[] | null;
  onClose: () => void;
}

const TAB_LABELS: Record<Tab, string> = {
  paid: "Payées",
  committed: "Engagées",
  forecast: "Prévisionnel",
};

export function CellEditorDrawer({
  open,
  month,
  categoryId,
  entityId,
  scenarioId,
  accountIds: _accountIds,
  onClose,
}: Props) {
  const [tab, setTab] = useState<Tab>("forecast");

  // Close on ESC
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const categoriesQuery = useCategories();
  const categoryName = useMemo(() => {
    const c = categoriesQuery.data?.find((x) => x.id === categoryId);
    return c?.name ?? `Catégorie #${categoryId}`;
  }, [categoriesQuery.data, categoryId]);

  const from = firstDayOfMonth(month);
  const to = lastDayOfMonth(month);

  // Tab content data
  const txQuery = useQuery({
    queryKey: [
      "forecast-drawer-transactions",
      entityId,
      categoryId,
      from,
      to,
    ],
    queryFn: () =>
      fetchTransactions({
        entity_id: entityId,
        date_from: from,
        date_to: to,
        per_page: 200,
      }),
    enabled: open && tab === "paid",
  });

  const commitmentsQuery = useCommitments({
    entityId,
    status: "pending",
    from,
    to,
  });

  const linesQuery = useLines(scenarioId);
  const currentLine =
    linesQuery.data?.find((l) => l.category_id === categoryId) ?? null;

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true">
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="absolute right-0 top-0 flex h-full w-[420px] flex-col border-l border-line-soft bg-panel shadow-xl">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-line-soft px-5 py-4">
          <div className="min-w-0">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              {formatMonthLabel(month, "long")}
            </div>
            <h2 className="mt-0.5 truncate text-[15px] font-semibold text-ink">
              {categoryName}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fermer"
            className="rounded-md p-1 text-ink-2 hover:bg-panel-2 hover:text-ink"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={1.75}
              strokeLinecap="round"
              strokeLinejoin="round"
              className="h-4 w-4"
            >
              <path d="M6 6l12 12" />
              <path d="M18 6L6 18" />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 border-b border-line-soft px-4">
          {(Object.keys(TAB_LABELS) as Tab[]).map((k) => (
            <button
              key={k}
              type="button"
              onClick={() => setTab(k)}
              className={cn(
                "relative px-3 py-2 text-[12.5px] font-medium transition-colors",
                tab === k
                  ? "text-ink"
                  : "text-muted-foreground hover:text-ink-2",
              )}
            >
              {TAB_LABELS[k]}
              {tab === k && (
                <span
                  aria-hidden
                  className="absolute inset-x-0 -bottom-px h-0.5 bg-accent"
                />
              )}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          {tab === "paid" && (
            <PaidTab
              loading={txQuery.isLoading}
              items={
                txQuery.data?.items.filter(
                  (t) => t.category?.id === categoryId,
                ) ?? []
              }
            />
          )}
          {tab === "committed" && (
            <CommittedTab
              loading={commitmentsQuery.isLoading}
              items={
                commitmentsQuery.data?.items.filter(
                  (c) => c.category_id === categoryId,
                ) ?? []
              }
            />
          )}
          {tab === "forecast" && (
            <MethodForm
              scenarioId={scenarioId}
              categoryId={categoryId}
              line={currentLine}
              onSave={onClose}
            />
          )}
        </div>
      </div>
    </div>
  );
}

function PaidTab({
  loading,
  items,
}: {
  loading: boolean;
  items: {
    id: number;
    operation_date: string;
    label: string;
    amount: string;
  }[];
}) {
  if (loading)
    return (
      <div className="py-8 text-center text-[12.5px] text-muted-foreground">
        Chargement…
      </div>
    );
  if (items.length === 0)
    return (
      <div className="py-8 text-center text-[12.5px] text-muted-foreground">
        Aucune transaction payée ce mois pour cette catégorie.
      </div>
    );
  return (
    <ul className="space-y-1.5">
      {items.map((t) => {
        const cents = Math.round(Number(t.amount) * 100);
        return (
          <li
            key={t.id}
            className="flex items-center justify-between gap-3 rounded-md border border-line-soft bg-panel-2/40 px-3 py-2"
          >
            <div className="min-w-0 flex-1">
              <div className="truncate text-[12.5px] text-ink">{t.label}</div>
              <div className="text-[11px] text-muted-foreground">
                {new Date(t.operation_date).toLocaleDateString("fr-FR")}
              </div>
            </div>
            <span
              className={cn(
                "font-mono text-[12.5px] tabular-nums",
                cents >= 0 ? "text-emerald-700" : "text-rose-700",
              )}
            >
              {formatCents(cents)}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

function CommittedTab({
  loading,
  items,
}: {
  loading: boolean;
  items: {
    id: number;
    amount_cents: number;
    direction: "in" | "out";
    expected_date: string;
    description: string | null;
    counterparty_name: string | null;
    reference: string | null;
  }[];
}) {
  if (loading)
    return (
      <div className="py-8 text-center text-[12.5px] text-muted-foreground">
        Chargement…
      </div>
    );
  if (items.length === 0)
    return (
      <div className="py-8 text-center text-[12.5px] text-muted-foreground">
        Aucun engagement en attente pour cette catégorie.
      </div>
    );
  return (
    <ul className="space-y-1.5">
      {items.map((c) => {
        const signed =
          c.direction === "out" ? -c.amount_cents : c.amount_cents;
        return (
          <li
            key={c.id}
            className="flex items-center justify-between gap-3 rounded-md border border-line-soft bg-panel-2/40 px-3 py-2"
          >
            <div className="min-w-0 flex-1">
              <div className="truncate text-[12.5px] text-ink">
                {c.counterparty_name ??
                  c.description ??
                  c.reference ??
                  "Engagement"}
              </div>
              <div className="text-[11px] text-muted-foreground">
                {new Date(c.expected_date).toLocaleDateString("fr-FR")}
              </div>
            </div>
            <span
              className={cn(
                "font-mono text-[12.5px] tabular-nums",
                signed >= 0 ? "text-emerald-700" : "text-rose-700",
              )}
            >
              {formatCents(signed)}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
