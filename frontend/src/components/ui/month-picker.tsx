/**
 * MonthPicker — sélecteur de mois stylé, jumeau de `DatePicker` mais
 * granularité mois entier.
 *
 * Remplace les `<input type="month">` natifs (rendu navigateur, hors charte).
 * Format échangé : "YYYY-MM" (compatible HTML5 et schémas backend).
 *
 * Usage :
 *   <MonthPicker value="2026-05" onChange={(ym) => ...} />
 */
import { useMemo, useState } from "react";

import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";

interface Props {
  value: string; // "YYYY-MM" ou "" si non défini
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
  /** Bornes inclusives au format "YYYY-MM". */
  min?: string;
  max?: string;
  id?: string;
  "aria-label"?: string;
}

const MONTH_LABELS = [
  "Janv",
  "Févr",
  "Mars",
  "Avril",
  "Mai",
  "Juin",
  "Juil",
  "Août",
  "Sept",
  "Oct",
  "Nov",
  "Déc",
];
const MONTH_NAMES = [
  "Janvier",
  "Février",
  "Mars",
  "Avril",
  "Mai",
  "Juin",
  "Juillet",
  "Août",
  "Septembre",
  "Octobre",
  "Novembre",
  "Décembre",
];

function parseYM(s: string): { year: number; month: number } | null {
  if (!s) return null;
  const m = /^(\d{4})-(\d{2})$/.exec(s);
  if (!m) return null;
  const year = Number(m[1]);
  const month = Number(m[2]);
  if (year < 1900 || year > 2999 || month < 1 || month > 12) return null;
  return { year, month };
}

function toYM(year: number, month: number): string {
  return `${year}-${String(month).padStart(2, "0")}`;
}

/** Comparaison "YYYY-MM" sous forme numérique (yyyy * 12 + mm). */
function ymRank(year: number, month: number): number {
  return year * 12 + month;
}

function formatDisplay(year: number, month: number): string {
  return `${MONTH_NAMES[month - 1]} ${year}`;
}

export function MonthPicker({
  value,
  onChange,
  placeholder = "Choisir un mois",
  className,
  disabled = false,
  min,
  max,
  id,
  "aria-label": ariaLabel,
}: Props) {
  const selected = useMemo(() => parseYM(value), [value]);
  const today = useMemo(() => {
    const d = new Date();
    return { year: d.getFullYear(), month: d.getMonth() + 1 };
  }, []);
  const [viewYear, setViewYear] = useState<number>(
    () => selected?.year ?? today.year,
  );
  const [open, setOpen] = useState(false);

  const minYM = useMemo(() => parseYM(min ?? ""), [min]);
  const maxYM = useMemo(() => parseYM(max ?? ""), [max]);

  function isDisabled(year: number, month: number): boolean {
    if (minYM && ymRank(year, month) < ymRank(minYM.year, minYM.month))
      return true;
    if (maxYM && ymRank(year, month) > ymRank(maxYM.year, maxYM.month))
      return true;
    return false;
  }

  function pick(year: number, month: number) {
    if (isDisabled(year, month)) return;
    onChange(toYM(year, month));
    setOpen(false);
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          id={id}
          aria-label={ariaLabel ?? "Sélectionner un mois"}
          disabled={disabled}
          className={cn(
            "flex h-9 w-full items-center justify-between rounded-md border border-line bg-panel px-3 py-1.5 text-[13px] text-ink transition-colors",
            "hover:border-ink-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/40",
            "disabled:cursor-not-allowed disabled:opacity-50",
            !selected && "text-muted-foreground",
            className,
          )}
        >
          <span>
            {selected ? formatDisplay(selected.year, selected.month) : placeholder}
          </span>
          <svg
            aria-hidden
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={1.6}
            strokeLinecap="round"
            strokeLinejoin="round"
            className="h-3.5 w-3.5 text-muted-foreground"
          >
            <rect x="3" y="4" width="18" height="18" rx="2" />
            <path d="M16 2v4M8 2v4M3 10h18" />
          </svg>
        </button>
      </PopoverTrigger>
      <PopoverContent
        align="start"
        className="w-[252px] border border-line-soft bg-panel p-3 shadow-card"
      >
        <div className="mb-2 flex items-center justify-between">
          <button
            type="button"
            onClick={() => setViewYear((y) => y - 1)}
            aria-label="Année précédente"
            className="rounded-md px-2 py-1 text-[14px] text-ink-2 hover:bg-panel-2"
          >
            ‹
          </button>
          <div className="text-[13px] font-semibold text-ink">{viewYear}</div>
          <button
            type="button"
            onClick={() => setViewYear((y) => y + 1)}
            aria-label="Année suivante"
            className="rounded-md px-2 py-1 text-[14px] text-ink-2 hover:bg-panel-2"
          >
            ›
          </button>
        </div>

        <div className="grid grid-cols-3 gap-1">
          {MONTH_LABELS.map((label, idx) => {
            const month = idx + 1;
            const isSelected =
              selected !== null &&
              selected.year === viewYear &&
              selected.month === month;
            const isCurrentMonth =
              today.year === viewYear && today.month === month;
            const disabledCell = isDisabled(viewYear, month);
            return (
              <button
                key={month}
                type="button"
                onClick={() => pick(viewYear, month)}
                disabled={disabledCell}
                className={cn(
                  "h-9 rounded-md text-center text-[12.5px] tabular-nums transition-colors",
                  !isSelected && "text-ink hover:bg-panel-2",
                  isSelected && "bg-accent text-white hover:bg-accent",
                  isCurrentMonth && !isSelected && "ring-1 ring-accent/40",
                  disabledCell && "cursor-not-allowed opacity-30",
                )}
              >
                {label}
              </button>
            );
          })}
        </div>

        <div className="mt-2 flex items-center justify-between border-t border-line-soft pt-2">
          <button
            type="button"
            onClick={() => {
              setViewYear(today.year);
              pick(today.year, today.month);
            }}
            className="rounded-md px-2 py-1 text-[12px] text-ink-2 hover:bg-panel-2"
          >
            Ce mois-ci
          </button>
          {selected && (
            <button
              type="button"
              onClick={() => {
                onChange("");
                setOpen(false);
              }}
              className="rounded-md px-2 py-1 text-[12px] text-muted-foreground hover:bg-panel-2"
            >
              Effacer
            </button>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}
