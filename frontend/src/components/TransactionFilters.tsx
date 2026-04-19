import type { TransactionFilter } from "../types/api";

export interface TransactionFiltersProps {
  value: TransactionFilter;
  onChange: (patch: TransactionFilter) => void;
}

export function TransactionFilters({ value, onChange }: TransactionFiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="relative flex-1 min-w-[240px]">
        <svg
          aria-hidden
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          className="pointer-events-none absolute left-3 top-1/2 h-[14px] w-[14px] -translate-y-1/2 text-muted-foreground"
        >
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.3-4.3" />
        </svg>
        <input
          type="search"
          placeholder="Rechercher par libellé, contrepartie, montant…"
          value={value.search ?? ""}
          onChange={(e) => onChange({ ...value, search: e.target.value || undefined, page: 1 })}
          className="w-full rounded-md border border-line bg-panel py-1.5 pl-9 pr-3 text-[12.5px] text-ink outline-none placeholder:text-muted-foreground focus:border-ink-2"
        />
      </div>
      <label className="flex items-center gap-1.5 rounded-md border border-line bg-panel px-2.5 py-1.5 text-[12.5px] text-ink-2">
        <span className="text-muted-foreground">du</span>
        <input
          type="date"
          value={value.date_from ?? ""}
          onChange={(e) => onChange({ ...value, date_from: e.target.value || undefined, page: 1 })}
          className="bg-transparent text-[12.5px] text-ink outline-none"
        />
      </label>
      <label className="flex items-center gap-1.5 rounded-md border border-line bg-panel px-2.5 py-1.5 text-[12.5px] text-ink-2">
        <span className="text-muted-foreground">au</span>
        <input
          type="date"
          value={value.date_to ?? ""}
          onChange={(e) => onChange({ ...value, date_to: e.target.value || undefined, page: 1 })}
          className="bg-transparent text-[12.5px] text-ink outline-none"
        />
      </label>
    </div>
  );
}
