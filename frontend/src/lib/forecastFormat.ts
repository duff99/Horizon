/**
 * Formatting helpers for the forecast v2 UI (prévisionnel).
 *
 * Months are handled as YYYY-MM strings to mirror the backend serialization.
 */

const MONTH_SHORT = new Intl.DateTimeFormat("fr-FR", {
  month: "short",
  year: "2-digit",
});

const MONTH_LONG = new Intl.DateTimeFormat("fr-FR", {
  month: "long",
  year: "numeric",
});

const INT_FR = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 });

/** "2026-01" → "janv. 26" (short) or "janvier 2026" (long). */
export function formatMonthLabel(
  yyyyMm: string,
  variant: "short" | "long" = "short",
): string {
  const [y, m] = yyyyMm.split("-");
  const d = new Date(Number(y), Number(m) - 1, 1);
  const raw = (variant === "long" ? MONTH_LONG : MONTH_SHORT).format(d);
  // Capitalize first letter for short form ("janv. 26" → "Janv. 26")
  if (variant === "short") {
    return raw.charAt(0).toUpperCase() + raw.slice(1);
  }
  return raw.charAt(0).toUpperCase() + raw.slice(1);
}

/** Format an integer cents value as "1 234 €" in French locale. */
export function formatCents(cents: number | null | undefined): string {
  if (cents == null) return "—";
  const v = Math.round(cents / 100);
  return `${INT_FR.format(v)} €`;
}

/** "2026-04" → "2026-04-01" (first day) as ISO date string. */
export function firstDayOfMonth(yyyyMm: string): string {
  return `${yyyyMm}-01`;
}

/** "2026-04" → "2026-04-30" (last day) as ISO date string. */
export function lastDayOfMonth(yyyyMm: string): string {
  const [y, m] = yyyyMm.split("-").map(Number);
  // day=0 of next month = last day of this month
  const d = new Date(y, m, 0);
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyyMm}-${dd}`;
}

/** Current month as "YYYY-MM" (local time). */
export function currentMonthStr(now: Date = new Date()): string {
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  return `${y}-${m}`;
}

/** Shift a YYYY-MM by N months (positive or negative). */
export function shiftMonth(yyyyMm: string, delta: number): string {
  const [y, m] = yyyyMm.split("-").map(Number);
  const d = new Date(y, m - 1 + delta, 1);
  const ny = d.getFullYear();
  const nm = String(d.getMonth() + 1).padStart(2, "0");
  return `${ny}-${nm}`;
}
