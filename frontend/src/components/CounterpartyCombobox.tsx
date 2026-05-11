import { useEffect, useMemo, useRef, useState } from "react";
import { Check, ChevronDown, Search, X } from "lucide-react";
import { cn } from "@/lib/utils";

export interface CounterpartyOption {
  id: number;
  name: string;
}

interface Props {
  counterparties: CounterpartyOption[];
  value: number | null;
  onChange: (id: number | null) => void;
  placeholder?: string;
  disabled?: boolean;
}

export function CounterpartyCombobox({
  counterparties,
  value,
  onChange,
  placeholder,
  disabled = false,
}: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const selected = useMemo(
    () => counterparties.find((cp) => cp.id === value) ?? null,
    [counterparties, value],
  );

  useEffect(() => {
    if (!open) return;
    const handler = (e: PointerEvent) => {
      const target = e.target as Node | null;
      if (target && rootRef.current && !rootRef.current.contains(target)) {
        setOpen(false);
      }
    };
    document.addEventListener("pointerdown", handler, true);
    return () => document.removeEventListener("pointerdown", handler, true);
  }, [open]);

  useEffect(() => {
    if (open) {
      const t = setTimeout(() => inputRef.current?.focus(), 0);
      return () => clearTimeout(t);
    }
    setQuery("");
  }, [open]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return counterparties;
    return counterparties.filter((cp) => cp.name.toLowerCase().includes(q));
  }, [counterparties, query]);

  function handleSelect(id: number) {
    onChange(id);
    setOpen(false);
  }

  return (
    <div ref={rootRef} className="relative flex items-center gap-1">
      <button
        type="button"
        role="combobox"
        aria-expanded={open}
        disabled={disabled}
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "flex h-[34px] w-[220px] items-center justify-between rounded-md border border-line bg-panel px-3 text-[12.5px] text-ink",
          "hover:border-ink-2 focus:outline-none focus:ring-2 focus:ring-accent/40",
          !selected && "text-muted-foreground",
          disabled && "cursor-not-allowed opacity-60",
        )}
      >
        <span className="truncate">
          {selected?.name ?? (placeholder ?? "Filtrer par tiers…")}
        </span>
        <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-60" aria-hidden />
      </button>
      {value != null && !disabled && (
        <button
          type="button"
          onClick={() => onChange(null)}
          aria-label="Retirer le filtre tiers"
          className="rounded-md border border-line-soft p-1.5 text-muted-foreground transition-colors hover:bg-panel-2 hover:text-ink"
        >
          <X className="h-3.5 w-3.5" aria-hidden />
        </button>
      )}

      {open && (
        <div
          className="absolute left-0 top-[calc(100%+4px)] z-50 w-[280px] overflow-hidden rounded-md border border-line bg-panel shadow-lg"
          role="listbox"
        >
          <div className="flex items-center border-b border-line-soft px-2.5">
            <Search className="mr-2 h-3.5 w-3.5 shrink-0 opacity-50" aria-hidden />
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Rechercher…"
              className="h-9 w-full bg-transparent text-[13px] outline-none placeholder:text-muted-foreground"
            />
          </div>
          <div className="max-h-[280px] overflow-y-auto p-1">
            {filtered.length === 0 ? (
              <div className="px-3 py-6 text-center text-[12.5px] text-muted-foreground">
                Aucun tiers
              </div>
            ) : (
              filtered.map((cp) => (
                <button
                  type="button"
                  key={cp.id}
                  onClick={() => handleSelect(cp.id)}
                  className={cn(
                    "flex w-full cursor-pointer items-center justify-between rounded-sm px-2 py-1.5 text-left text-[13px] text-ink-2",
                    "hover:bg-panel-2 hover:text-ink",
                    value === cp.id && "bg-accent/15 text-ink",
                  )}
                >
                  <span className="truncate">{cp.name}</span>
                  {value === cp.id && (
                    <Check className="h-3.5 w-3.5 text-accent" aria-hidden />
                  )}
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
