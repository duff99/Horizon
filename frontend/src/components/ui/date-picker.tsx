/**
 * DatePicker — sélecteur de date stylé, cohérent avec le design de l'app.
 *
 * Remplace les `<input type="date">` natifs (au rendu différent selon
 * navigateurs et hors-style global). Utilise le composant Popover Radix
 * et une grille HTML maison ; pas de dépendance supplémentaire.
 *
 * Format échangé : ISO "YYYY-MM-DD" pour rester compatible avec les
 * inputs date HTML5 et les schémas backend (Pydantic / FastAPI).
 *
 * Usage :
 *   <DatePicker value="2026-04-28" onChange={(iso) => ...} />
 *   <DatePicker value="" onChange={...} placeholder="Choisir une date" />
 */
import { useMemo, useState } from "react";

import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";

interface Props {
  value: string; // "YYYY-MM-DD" ou "" si non défini
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
  /**
   * Date min/max (incluse) au format ISO. Permet d'interdire des plages
   * incohérentes (ex. : date d'émission ≤ date prévue dans Engagements).
   */
  min?: string;
  max?: string;
  id?: string;
  "aria-label"?: string;
}

const DAY_LABELS = ["L", "M", "M", "J", "V", "S", "D"];
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

function parseISO(s: string): Date | null {
  if (!s) return null;
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
  if (!m) return null;
  const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  return Number.isNaN(d.getTime()) ? null : d;
}

function toISO(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function sameYMD(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

function formatDisplay(d: Date): string {
  return d.toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

/**
 * Construit la grille du mois affiché. Lundi = premier jour de semaine,
 * comme la convention française. La grille est complétée avec les jours
 * du mois précédent / suivant pour atteindre 6 lignes × 7 colonnes (max).
 */
function buildMonthGrid(view: Date): { date: Date; outside: boolean }[] {
  const firstOfMonth = new Date(view.getFullYear(), view.getMonth(), 1);
  // getDay : 0=dimanche..6=samedi → on convertit en 0=lundi..6=dimanche
  const offset = (firstOfMonth.getDay() + 6) % 7;
  const start = new Date(firstOfMonth);
  start.setDate(start.getDate() - offset);

  const grid: { date: Date; outside: boolean }[] = [];
  for (let i = 0; i < 42; i++) {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    grid.push({
      date: d,
      outside: d.getMonth() !== view.getMonth(),
    });
    // On coupe à 6 semaines mais arrête plus tôt si la dernière ligne
    // entière est déjà hors-mois (mois court qui tient en 5 lignes).
    if (
      i >= 27 &&
      (i + 1) % 7 === 0 &&
      d.getMonth() !== view.getMonth()
    ) {
      break;
    }
  }
  return grid;
}

export function DatePicker({
  value,
  onChange,
  placeholder = "Choisir une date",
  className,
  disabled = false,
  min,
  max,
  id,
  "aria-label": ariaLabel,
}: Props) {
  const selected = useMemo(() => parseISO(value), [value]);
  const [view, setView] = useState<Date>(() => selected ?? new Date());
  const [open, setOpen] = useState(false);

  const minDate = useMemo(() => parseISO(min ?? ""), [min]);
  const maxDate = useMemo(() => parseISO(max ?? ""), [max]);
  const today = useMemo(() => new Date(), []);
  const grid = useMemo(() => buildMonthGrid(view), [view]);

  function handlePick(d: Date) {
    if (minDate && d < minDate) return;
    if (maxDate && d > maxDate) return;
    onChange(toISO(d));
    setOpen(false);
  }

  function nav(months: number) {
    setView(new Date(view.getFullYear(), view.getMonth() + months, 1));
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          id={id}
          aria-label={ariaLabel ?? "Sélectionner une date"}
          disabled={disabled}
          className={cn(
            "flex h-9 w-full items-center justify-between rounded-md border border-line bg-panel px-3 py-1.5 text-[13px] text-ink transition-colors",
            "hover:border-ink-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/40",
            "disabled:cursor-not-allowed disabled:opacity-50",
            !selected && "text-muted-foreground",
            className,
          )}
        >
          <span>{selected ? formatDisplay(selected) : placeholder}</span>
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
        className="w-[296px] border border-line-soft bg-panel p-3 shadow-card"
      >
        <div className="mb-2 flex items-center justify-between">
          <button
            type="button"
            onClick={() => nav(-1)}
            aria-label="Mois précédent"
            className="rounded-md px-2 py-1 text-[14px] text-ink-2 hover:bg-panel-2"
          >
            ‹
          </button>
          <div className="text-[13px] font-semibold text-ink">
            {MONTH_NAMES[view.getMonth()]} {view.getFullYear()}
          </div>
          <button
            type="button"
            onClick={() => nav(1)}
            aria-label="Mois suivant"
            className="rounded-md px-2 py-1 text-[14px] text-ink-2 hover:bg-panel-2"
          >
            ›
          </button>
        </div>

        <div className="mb-1 grid grid-cols-7 gap-0.5 text-center text-[10.5px] font-semibold uppercase tracking-wider text-muted-foreground">
          {DAY_LABELS.map((d, i) => (
            <span key={i}>{d}</span>
          ))}
        </div>

        <div className="grid grid-cols-7 gap-0.5">
          {grid.map(({ date, outside }) => {
            const isSelected = selected ? sameYMD(date, selected) : false;
            const isToday = sameYMD(date, today);
            const beforeMin = minDate ? date < minDate : false;
            const afterMax = maxDate ? date > maxDate : false;
            const isDisabled = beforeMin || afterMax;
            return (
              <button
                key={date.toISOString()}
                type="button"
                onClick={() => handlePick(date)}
                disabled={isDisabled}
                className={cn(
                  "h-8 rounded-md text-center text-[12.5px] tabular-nums transition-colors",
                  outside && "text-muted-foreground/50",
                  !outside && !isSelected && "text-ink hover:bg-panel-2",
                  isSelected && "bg-accent text-white hover:bg-accent",
                  isToday && !isSelected && "ring-1 ring-accent/40",
                  isDisabled && "cursor-not-allowed opacity-30",
                )}
              >
                {date.getDate()}
              </button>
            );
          })}
        </div>

        <div className="mt-2 flex items-center justify-between border-t border-line-soft pt-2">
          <button
            type="button"
            onClick={() => {
              const t = new Date();
              setView(t);
              handlePick(t);
            }}
            className="rounded-md px-2 py-1 text-[12px] text-ink-2 hover:bg-panel-2"
          >
            Aujourd'hui
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
