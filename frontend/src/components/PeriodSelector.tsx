/**
 * PeriodSelector — sélecteur de période réutilisable avec presets + plage personnalisée.
 *
 * Utilisé sur Dashboard, Forecast v2 (granularité mois), Imports, Transactions.
 * Helpers `computeRange` et `formatPeriodForDisplay` exportés pour usage externe.
 */
import { useMemo } from "react";

export type PeriodPreset =
  | "30d"
  | "90d"
  | "12m"
  | "ytd"
  | "previous_month"
  | "custom";

export interface PeriodValue {
  from: string; // YYYY-MM-DD (ou YYYY-MM si granularité month)
  to: string;
  preset: PeriodPreset;
}

interface Props {
  value: PeriodValue;
  onChange: (v: PeriodValue) => void;
  granularity?: "day" | "month";
  className?: string;
  /**
   * Liste des presets visibles. Par défaut : 30d, 90d, 12m, ytd, previous_month, custom.
   * En mode month, "30d" et "90d" sont automatiquement masqués si pas listés explicitement.
   */
  presets?: PeriodPreset[];
}

// ---------------------------------------------------------------------------
// Date helpers
// ---------------------------------------------------------------------------

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

function formatISODate(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function formatISOMonth(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}`;
}

function lastDayOfMonth(year: number, month: number): Date {
  // month is 1-based here. day=0 of next month = last day of current.
  return new Date(year, month, 0);
}

/**
 * Calcule les bornes ISO YYYY-MM-DD pour un preset donné.
 * Pour `custom`, renvoie les dernières bornes connues (ou 30d par défaut).
 */
export function computeRange(
  preset: PeriodPreset,
  today: Date = new Date(),
): { from: string; to: string } {
  const t = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  switch (preset) {
    case "30d": {
      const from = new Date(t);
      from.setDate(from.getDate() - 29);
      return { from: formatISODate(from), to: formatISODate(t) };
    }
    case "90d": {
      const from = new Date(t);
      from.setDate(from.getDate() - 89);
      return { from: formatISODate(from), to: formatISODate(t) };
    }
    case "12m": {
      const from = new Date(t);
      from.setMonth(from.getMonth() - 11);
      from.setDate(1);
      return { from: formatISODate(from), to: formatISODate(t) };
    }
    case "ytd": {
      const from = new Date(t.getFullYear(), 0, 1);
      return { from: formatISODate(from), to: formatISODate(t) };
    }
    case "previous_month": {
      const firstOfThis = new Date(t.getFullYear(), t.getMonth(), 1);
      const end = new Date(firstOfThis);
      end.setDate(end.getDate() - 1);
      const from = new Date(end.getFullYear(), end.getMonth(), 1);
      return { from: formatISODate(from), to: formatISODate(end) };
    }
    case "custom":
    default: {
      // Fallback sensible : 30 derniers jours
      const from = new Date(t);
      from.setDate(from.getDate() - 29);
      return { from: formatISODate(from), to: formatISODate(t) };
    }
  }
}

/**
 * Variante "month" de computeRange : renvoie YYYY-MM.
 * 12m : 12 mois glissants se terminant au mois courant.
 */
export function computeMonthRange(
  preset: PeriodPreset,
  today: Date = new Date(),
): { from: string; to: string } {
  const t = new Date(today.getFullYear(), today.getMonth(), 1);
  switch (preset) {
    case "12m": {
      const from = new Date(t);
      from.setMonth(from.getMonth() - 11);
      return { from: formatISOMonth(from), to: formatISOMonth(t) };
    }
    case "ytd": {
      const from = new Date(t.getFullYear(), 0, 1);
      return { from: formatISOMonth(from), to: formatISOMonth(t) };
    }
    case "previous_month": {
      const from = new Date(t.getFullYear(), t.getMonth() - 1, 1);
      return { from: formatISOMonth(from), to: formatISOMonth(from) };
    }
    case "30d":
    case "90d":
    case "custom":
    default: {
      const from = new Date(t);
      from.setMonth(from.getMonth() - 11);
      return { from: formatISOMonth(from), to: formatISOMonth(t) };
    }
  }
}

// ---------------------------------------------------------------------------
// Display helpers
// ---------------------------------------------------------------------------

const FR_DATE = new Intl.DateTimeFormat("fr-FR", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});

const FR_MONTH = new Intl.DateTimeFormat("fr-FR", {
  month: "long",
  year: "numeric",
});

function parseDate(s: string): Date {
  // "YYYY-MM-DD" ou "YYYY-MM"
  const parts = s.split("-").map(Number);
  const y = parts[0];
  const m = parts[1] ?? 1;
  const d = parts[2] ?? 1;
  return new Date(y, m - 1, d);
}

export function formatPeriodForDisplay(v: PeriodValue): string {
  switch (v.preset) {
    case "30d":
      return "30 derniers jours";
    case "90d":
      return "90 derniers jours";
    case "12m":
      return "12 derniers mois";
    case "ytd":
      return "Année en cours";
    case "previous_month": {
      const d = parseDate(v.from);
      return FR_MONTH.format(d).replace(/^./, (c) => c.toUpperCase());
    }
    case "custom":
    default: {
      try {
        return `${FR_DATE.format(parseDate(v.from))} → ${FR_DATE.format(parseDate(v.to))}`;
      } catch {
        return "Personnalisé";
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const PRESET_LABELS: Record<PeriodPreset, string> = {
  "30d": "30 j",
  "90d": "90 j",
  "12m": "12 m",
  ytd: "Année",
  previous_month: "Mois-1",
  custom: "Perso.",
};

const DEFAULT_PRESETS_DAY: PeriodPreset[] = [
  "30d",
  "90d",
  "12m",
  "ytd",
  "previous_month",
  "custom",
];

const DEFAULT_PRESETS_MONTH: PeriodPreset[] = [
  "12m",
  "ytd",
  "previous_month",
  "custom",
];

export function PeriodSelector({
  value,
  onChange,
  granularity = "day",
  className,
  presets,
}: Props) {
  const effectivePresets = useMemo(() => {
    if (presets) return presets;
    return granularity === "month"
      ? DEFAULT_PRESETS_MONTH
      : DEFAULT_PRESETS_DAY;
  }, [presets, granularity]);

  const handlePresetClick = (preset: PeriodPreset) => {
    if (preset === "custom") {
      onChange({ ...value, preset: "custom" });
      return;
    }
    const range =
      granularity === "month" ? computeMonthRange(preset) : computeRange(preset);
    onChange({ from: range.from, to: range.to, preset });
  };

  const isMonthInput = granularity === "month";
  const inputType = isMonthInput ? "month" : "date";

  return (
    <div
      className={
        "inline-flex items-center gap-2 rounded-md border border-line-soft bg-panel shadow-card h-9 px-1 " +
        (className ?? "")
      }
      role="group"
      aria-label="Période"
    >
      <div className="inline-flex items-center gap-0.5">
        {effectivePresets.map((p) => {
          const active = value.preset === p;
          return (
            <button
              key={p}
              type="button"
              aria-pressed={active}
              onClick={() => handlePresetClick(p)}
              className={
                "px-2.5 py-1 text-[12.5px] rounded-sm transition-colors " +
                (active
                  ? "bg-ink text-white"
                  : "text-ink-2 hover:bg-black/5")
              }
            >
              {PRESET_LABELS[p]}
            </button>
          );
        })}
      </div>

      {value.preset === "custom" && (
        <div className="ml-1 flex items-center gap-1 border-l border-line-soft pl-2">
          <input
            type={inputType}
            aria-label="Date de début"
            value={value.from}
            onChange={(e) =>
              onChange({ ...value, from: e.target.value, preset: "custom" })
            }
            className="h-7 border border-line-soft bg-white rounded-sm px-2 text-[12.5px] text-ink font-mono tabular-nums focus:outline-none focus:ring-1 focus:ring-accent/40"
          />
          <span className="text-[12.5px] text-muted-foreground">→</span>
          <input
            type={inputType}
            aria-label="Date de fin"
            value={value.to}
            onChange={(e) =>
              onChange({ ...value, to: e.target.value, preset: "custom" })
            }
            className="h-7 border border-line-soft bg-white rounded-sm px-2 text-[12.5px] text-ink font-mono tabular-nums focus:outline-none focus:ring-1 focus:ring-accent/40"
          />
        </div>
      )}
    </div>
  );
}

/**
 * Helper : construit un PeriodValue par défaut selon granularité.
 */
export function defaultPeriodValue(
  preset: PeriodPreset = "30d",
  granularity: "day" | "month" = "day",
  today: Date = new Date(),
): PeriodValue {
  const range =
    granularity === "month"
      ? computeMonthRange(preset, today)
      : computeRange(preset, today);
  return { from: range.from, to: range.to, preset };
}

// Re-export for tests
export { lastDayOfMonth as _lastDayOfMonth };
