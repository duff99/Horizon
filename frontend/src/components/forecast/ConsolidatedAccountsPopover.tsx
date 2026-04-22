import { useEffect, useMemo, useState } from "react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { useBankAccounts } from "@/api/bankAccounts";
import { useForecastUi } from "@/stores/forecastUi";

interface Props {
  entityId: number | null;
}

export function ConsolidatedAccountsPopover({ entityId }: Props) {
  const { data: accounts = [] } = useBankAccounts();
  const accountIds = useForecastUi((s) => s.accountIds);
  const setAccountIds = useForecastUi((s) => s.setAccountIds);

  const entityAccounts = useMemo(
    () =>
      entityId == null
        ? []
        : accounts.filter((a) => a.entityId === entityId && a.isActive),
    [accounts, entityId],
  );

  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<Set<number>>(new Set());

  // When popover opens, initialize draft from current state
  useEffect(() => {
    if (!open) return;
    if (accountIds == null) {
      setDraft(new Set(entityAccounts.map((a) => a.id)));
    } else {
      setDraft(new Set(accountIds));
    }
  }, [open, accountIds, entityAccounts]);

  const total = entityAccounts.length;
  const allSelected = total > 0 && draft.size === total;

  const label = useMemo(() => {
    if (accountIds == null) return "Vue consolidée";
    if (accountIds.length === 0) return "Aucun compte";
    if (accountIds.length === entityAccounts.length) return "Vue consolidée";
    return `${accountIds.length} compte${accountIds.length > 1 ? "s" : ""} sélectionné${accountIds.length > 1 ? "s" : ""}`;
  }, [accountIds, entityAccounts.length]);

  function toggleAll() {
    if (allSelected) {
      setDraft(new Set());
    } else {
      setDraft(new Set(entityAccounts.map((a) => a.id)));
    }
  }

  function toggle(id: number) {
    setDraft((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function validate() {
    const ids = Array.from(draft).sort((a, b) => a - b);
    // If all accounts are selected, treat as "all" (null)
    if (ids.length === entityAccounts.length) {
      setAccountIds(null);
    } else {
      setAccountIds(ids);
    }
    setOpen(false);
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          disabled={entityId == null}
          className="h-9 gap-2 rounded-md border-line-soft bg-panel px-3 text-[12.5px] font-medium text-ink shadow-card hover:bg-panel-2 hover:text-ink"
        >
          <span
            aria-hidden
            className="flex h-5 w-5 shrink-0 items-center justify-center rounded-[5px] bg-accent/10 text-accent"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={1.75}
              strokeLinecap="round"
              strokeLinejoin="round"
              className="h-3 w-3"
            >
              <path d="M3 10l9-6 9 6" />
              <path d="M5 10v8" />
              <path d="M12 10v8" />
              <path d="M19 10v8" />
              <path d="M3 20h18" />
            </svg>
          </span>
          <span>{label}</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent
        align="end"
        className="w-[320px] border-line-soft bg-panel p-0 shadow-card"
      >
        <div className="flex items-center justify-between border-b border-line-soft px-3 py-2">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Comptes bancaires
          </span>
          <button
            type="button"
            onClick={toggleAll}
            className="text-[11.5px] text-accent hover:underline"
          >
            {allSelected ? "Tout désélectionner" : "Tout sélectionner"}
          </button>
        </div>
        <div className="max-h-[280px] overflow-y-auto px-2 py-2">
          {entityAccounts.length === 0 ? (
            <div className="px-2 py-4 text-center text-[12.5px] text-muted-foreground">
              Aucun compte actif pour cette entité.
            </div>
          ) : (
            entityAccounts.map((a) => (
              <label
                key={a.id}
                className="flex cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-[12.5px] text-ink hover:bg-panel-2"
              >
                <input
                  type="checkbox"
                  checked={draft.has(a.id)}
                  onChange={() => toggle(a.id)}
                  className="h-3.5 w-3.5 accent-accent"
                />
                <span className="min-w-0 flex-1 truncate">
                  {a.name}
                  <span className="ml-1 text-[11.5px] text-muted-foreground">
                    — {a.bankName}
                  </span>
                </span>
              </label>
            ))
          )}
        </div>
        <div className="flex items-center justify-end gap-2 border-t border-line-soft px-3 py-2">
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="rounded-md px-2.5 py-1 text-[12px] text-ink-2 hover:text-ink"
          >
            Annuler
          </button>
          <button
            type="button"
            onClick={validate}
            className="rounded-md bg-ink px-3 py-1 text-[12px] font-medium text-panel hover:bg-ink/90"
          >
            Valider
          </button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
