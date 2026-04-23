import { useMemo } from "react";
import type { TransactionFilter } from "../types/api";
import {
  PeriodSelector,
  computeRange,
  type PeriodPreset,
  type PeriodValue,
} from "./PeriodSelector";

export interface TransactionFiltersProps {
  value: TransactionFilter;
  onChange: (patch: TransactionFilter) => void;
}

/**
 * Déduit un preset à partir des date_from/date_to du filtre.
 * Si aucune des deux → preset "30d" avec from/to vides côté filtre (affichage neutre).
 * Si l'une ou l'autre correspond à un preset connu → on le restitue.
 * Sinon → "custom".
 */
function inferPreset(
  dateFrom: string | undefined,
  dateTo: string | undefined,
  today: Date = new Date(),
): PeriodValue {
  if (!dateFrom && !dateTo) {
    // État "tout" : on conserve preset custom vide pour éviter de filtrer.
    return { from: "", to: "", preset: "custom" };
  }
  const candidates: PeriodPreset[] = [
    "30d",
    "90d",
    "12m",
    "ytd",
    "previous_month",
  ];
  for (const p of candidates) {
    const r = computeRange(p, today);
    if (r.from === dateFrom && r.to === dateTo) {
      return { from: r.from, to: r.to, preset: p };
    }
  }
  return { from: dateFrom ?? "", to: dateTo ?? "", preset: "custom" };
}

export function TransactionFilters({ value, onChange }: TransactionFiltersProps) {
  const periodValue = useMemo(
    () => inferPreset(value.date_from, value.date_to),
    [value.date_from, value.date_to],
  );

  const handlePeriodChange = (v: PeriodValue) => {
    onChange({
      ...value,
      date_from: v.from || undefined,
      date_to: v.to || undefined,
      page: 1,
    });
  };

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
          placeholder="Rechercher par libellé, tiers, montant…"
          value={value.search ?? ""}
          onChange={(e) => onChange({ ...value, search: e.target.value || undefined, page: 1 })}
          className="w-full rounded-md border border-line bg-panel py-1.5 pl-9 pr-3 text-[12.5px] text-ink outline-none placeholder:text-muted-foreground focus:border-ink-2"
        />
      </div>
      <PeriodSelector value={periodValue} onChange={handlePeriodChange} />
    </div>
  );
}
