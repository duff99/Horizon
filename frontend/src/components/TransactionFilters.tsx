import type { TransactionFilter } from "../types/api";

export interface TransactionFiltersProps {
  value: TransactionFilter;
  onChange: (patch: TransactionFilter) => void;
}

export function TransactionFilters({ value, onChange }: TransactionFiltersProps) {
  return (
    <div className="flex flex-wrap gap-2">
      <input
        type="search"
        placeholder="Rechercher un libellé…"
        value={value.search ?? ""}
        onChange={(e) => onChange({ ...value, search: e.target.value || undefined, page: 1 })}
        className="rounded-md border px-3 py-2 text-sm"
      />
      <input
        type="date"
        value={value.date_from ?? ""}
        onChange={(e) => onChange({ ...value, date_from: e.target.value || undefined, page: 1 })}
        className="rounded-md border px-3 py-2 text-sm"
      />
      <input
        type="date"
        value={value.date_to ?? ""}
        onChange={(e) => onChange({ ...value, date_to: e.target.value || undefined, page: 1 })}
        className="rounded-md border px-3 py-2 text-sm"
      />
    </div>
  );
}
