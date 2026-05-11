import { useMemo } from "react";
import type { TransactionFilter } from "../types/api";
import {
  PeriodSelector,
  computeRange,
  type PeriodPreset,
  type PeriodValue,
} from "./PeriodSelector";
import { CategoryCombobox, type CategoryOption } from "./CategoryCombobox";
import { CounterpartyCombobox, type CounterpartyOption } from "./CounterpartyCombobox";
import { X } from "lucide-react";

export interface TransactionFiltersProps {
  value: TransactionFilter;
  onChange: (patch: TransactionFilter) => void;
  categories?: CategoryOption[];
  counterparties?: CounterpartyOption[];
  /**
   * Si true, masque le champ de recherche (le parent l'affiche déjà
   * ailleurs pour avoir un layout en deux rangées propre). Quand false
   * (défaut), conserve le comportement historique tout-en-une.
   */
  hideSearch?: boolean;
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

export function TransactionFilters({
  value,
  onChange,
  categories,
  counterparties,
  hideSearch = false,
}: TransactionFiltersProps) {
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

  const handleCategoryChange = (id: number | null) => {
    onChange({ ...value, category_id: id ?? undefined, page: 1 });
  };

  const handleCounterpartyChange = (id: number | null) => {
    onChange({ ...value, counterparty_id: id ?? undefined, page: 1 });
  };

  function handleAmountMinChange(e: React.ChangeEvent<HTMLInputElement>) {
    const raw = e.target.value;
    const val = raw === "" ? undefined : Number(raw);
    onChange({ ...value, amount_min: val, page: 1 });
  }

  function handleAmountMaxChange(e: React.ChangeEvent<HTMLInputElement>) {
    const raw = e.target.value;
    const val = raw === "" ? undefined : Number(raw);
    onChange({ ...value, amount_max: val, page: 1 });
  }

  function handleSepaChange(e: React.ChangeEvent<HTMLInputElement>) {
    onChange({ ...value, include_sepa_children: e.target.checked || undefined, page: 1 });
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {!hideSearch && (
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
      )}
      <PeriodSelector value={periodValue} onChange={handlePeriodChange} />
      {categories && categories.length > 0 && (
        <div className="flex min-w-[220px] items-center gap-1">
          <div className="flex-1">
            <CategoryCombobox
              categories={categories}
              value={value.category_id ?? null}
              onChange={handleCategoryChange}
              placeholder="Filtrer par catégorie…"
            />
          </div>
          {value.category_id != null && (
            <button
              type="button"
              onClick={() => handleCategoryChange(null)}
              aria-label="Retirer le filtre catégorie"
              className="rounded-md border border-line-soft p-1.5 text-muted-foreground transition-colors hover:bg-panel-2 hover:text-ink"
            >
              <X className="h-3.5 w-3.5" aria-hidden />
            </button>
          )}
        </div>
      )}
      {counterparties && counterparties.length > 0 && (
        <CounterpartyCombobox
          counterparties={counterparties}
          value={value.counterparty_id ?? null}
          onChange={handleCounterpartyChange}
          placeholder="Filtrer par tiers…"
        />
      )}
      {/* Filtres montant min / max (E8) */}
      <div className="flex items-center gap-1">
        <input
          id="amount-min"
          type="number"
          min="0"
          step="0.01"
          placeholder="Montant min (€)"
          value={value.amount_min ?? ""}
          onChange={handleAmountMinChange}
          aria-label="Montant minimum en euros"
          className="w-[130px] rounded-md border border-line bg-panel py-1.5 px-2.5 text-[12.5px] text-ink outline-none placeholder:text-muted-foreground focus:border-ink-2"
        />
        <span className="text-[12px] text-muted-foreground">–</span>
        <input
          id="amount-max"
          type="number"
          min="0"
          step="0.01"
          placeholder="Montant max (€)"
          value={value.amount_max ?? ""}
          onChange={handleAmountMaxChange}
          aria-label="Montant maximum en euros"
          className="w-[130px] rounded-md border border-line bg-panel py-1.5 px-2.5 text-[12.5px] text-ink outline-none placeholder:text-muted-foreground focus:border-ink-2"
        />
      </div>
      {/* Toggle SEPA détaillés (E7) */}
      <label className="flex items-center gap-2 cursor-pointer select-none">
        <input
          id="include-sepa"
          type="checkbox"
          checked={value.include_sepa_children ?? false}
          onChange={handleSepaChange}
          className="h-3.5 w-3.5 accent-ink"
        />
        <span className="text-[12.5px] text-ink-2">Afficher les virements SEPA détaillés</span>
      </label>
    </div>
  );
}
