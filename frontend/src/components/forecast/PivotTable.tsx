import { useMemo, useState } from "react";
import type { PivotResult, PivotRow } from "@/types/forecast";
import { formatCents, formatMonthLabel } from "@/lib/forecastFormat";
import { cn } from "@/lib/utils";

interface Props {
  result: PivotResult;
  onCellClick: (month: string, categoryId: number) => void;
  currentMonth: string;
}

interface RenderableRow {
  row: PivotRow;
  depth: number;
  hasChildren: boolean;
  parentChain: number[];
}

function buildHierarchy(
  rows: PivotRow[],
): { roots: PivotRow[]; childrenOf: Map<number, PivotRow[]> } {
  const childrenOf = new Map<number, PivotRow[]>();
  const ids = new Set(rows.map((r) => r.category_id));
  const roots: PivotRow[] = [];
  for (const r of rows) {
    if (r.parent_id != null && ids.has(r.parent_id)) {
      const list = childrenOf.get(r.parent_id) ?? [];
      list.push(r);
      childrenOf.set(r.parent_id, list);
    } else {
      roots.push(r);
    }
  }
  return { roots, childrenOf };
}

function flatten(
  roots: PivotRow[],
  childrenOf: Map<number, PivotRow[]>,
  expanded: Set<number>,
  depth = 0,
  chain: number[] = [],
): RenderableRow[] {
  const out: RenderableRow[] = [];
  for (const row of roots) {
    const kids = childrenOf.get(row.category_id) ?? [];
    out.push({
      row,
      depth,
      hasChildren: kids.length > 0,
      parentChain: chain,
    });
    if (kids.length > 0 && expanded.has(row.category_id)) {
      out.push(
        ...flatten(kids, childrenOf, expanded, depth + 1, [
          ...chain,
          row.category_id,
        ]),
      );
    }
  }
  return out;
}

export function PivotTable({ result, onCellClick, currentMonth }: Props) {
  const { months, rows: allRows } = result;

  const inRows = useMemo(
    () => allRows.filter((r) => r.direction === "in"),
    [allRows],
  );
  const outRows = useMemo(
    () => allRows.filter((r) => r.direction === "out"),
    [allRows],
  );

  const inHier = useMemo(() => buildHierarchy(inRows), [inRows]);
  const outHier = useMemo(() => buildHierarchy(outRows), [outRows]);

  // By default all roots are expanded. User toggles per category.
  const [expanded, setExpanded] = useState<Set<number>>(() => {
    const s = new Set<number>();
    for (const r of allRows) {
      if (r.parent_id == null) s.add(r.category_id);
    }
    return s;
  });

  const [inGroupOpen, setInGroupOpen] = useState(true);
  const [outGroupOpen, setOutGroupOpen] = useState(true);

  function toggle(categoryId: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(categoryId)) next.delete(categoryId);
      else next.add(categoryId);
      return next;
    });
  }

  const visibleIn = useMemo(
    () =>
      inGroupOpen ? flatten(inHier.roots, inHier.childrenOf, expanded) : [],
    [inHier, expanded, inGroupOpen],
  );
  const visibleOut = useMemo(
    () =>
      outGroupOpen
        ? flatten(outHier.roots, outHier.childrenOf, expanded)
        : [],
    [outHier, expanded, outGroupOpen],
  );

  // Monthly totals per direction (sum of ROOT rows only — they already
  // include their children thanks to the backend aggregation).
  const inTotals = useMemo(() => {
    return months.map((_m, idx) =>
      inHier.roots.reduce((s, r) => s + (r.cells[idx]?.total_cents ?? 0), 0),
    );
  }, [months, inHier.roots]);
  const outTotals = useMemo(() => {
    return months.map((_m, idx) =>
      outHier.roots.reduce((s, r) => s + (r.cells[idx]?.total_cents ?? 0), 0),
    );
  }, [months, outHier.roots]);

  const netByMonth = useMemo(
    () => months.map((_m, i) => inTotals[i] - outTotals[i]),
    [months, inTotals, outTotals],
  );

  // Opening balance per month = closing balance of previous month, or the
  // global opening_balance_cents for the first displayed month.
  const openingByMonth = useMemo(() => {
    const arr: number[] = [];
    for (let i = 0; i < months.length; i++) {
      if (i === 0) arr.push(result.opening_balance_cents);
      else arr.push(result.closing_balance_projection_cents[i - 1] ?? 0);
    }
    return arr;
  }, [months, result.opening_balance_cents, result.closing_balance_projection_cents]);

  return (
    <div className="overflow-x-auto rounded-xl border border-line-soft bg-panel shadow-card">
      <table className="min-w-full border-collapse text-[12.5px]">
        <thead>
          <tr className="border-b border-line-soft bg-panel-2">
            <th
              className="sticky left-0 z-20 min-w-[260px] bg-panel-2 px-4 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground"
              style={{ position: "sticky", left: 0 }}
            >
              Catégorie
            </th>
            {months.map((m) => (
              <th
                key={m}
                className={cn(
                  "px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground",
                  m === currentMonth && "text-accent",
                )}
              >
                {formatMonthLabel(m)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {/* Opening balance row */}
          <SummaryRow
            label="Trésorerie en début de mois"
            values={openingByMonth}
            months={months}
            currentMonth={currentMonth}
            tone="muted"
          />

          {/* Encaissements group */}
          <GroupHeaderRow
            label="Encaissements"
            open={inGroupOpen}
            onToggle={() => setInGroupOpen((v) => !v)}
            values={inTotals}
            months={months}
            currentMonth={currentMonth}
          />
          {visibleIn.map(({ row, depth, hasChildren }) => (
            <CategoryRow
              key={`in-${row.category_id}`}
              row={row}
              depth={depth}
              hasChildren={hasChildren}
              expanded={expanded.has(row.category_id)}
              onToggle={() => toggle(row.category_id)}
              onCellClick={onCellClick}
              currentMonth={currentMonth}
            />
          ))}

          {/* Décaissements group */}
          <GroupHeaderRow
            label="Décaissements"
            open={outGroupOpen}
            onToggle={() => setOutGroupOpen((v) => !v)}
            values={outTotals.map((v) => -v)}
            months={months}
            currentMonth={currentMonth}
          />
          {visibleOut.map(({ row, depth, hasChildren }) => (
            <CategoryRow
              key={`out-${row.category_id}`}
              row={row}
              depth={depth}
              hasChildren={hasChildren}
              expanded={expanded.has(row.category_id)}
              onToggle={() => toggle(row.category_id)}
              onCellClick={onCellClick}
              currentMonth={currentMonth}
              isOut
            />
          ))}

          {/* Net variation */}
          <SummaryRow
            label="Variation nette de cash"
            values={netByMonth}
            months={months}
            currentMonth={currentMonth}
            tone="emphasized"
          />

          {/* Closing balance */}
          <SummaryRow
            label="Trésorerie en fin de mois"
            values={result.closing_balance_projection_cents}
            months={months}
            currentMonth={currentMonth}
            tone="emphasized"
          />
        </tbody>
      </table>
    </div>
  );
}

function amountClass(cents: number, isFuture: boolean): string {
  const base = isFuture ? "italic " : "";
  if (cents > 0) return base + "text-emerald-700";
  if (cents < 0) return base + "text-rose-700";
  return base + "text-muted-foreground";
}

interface SummaryRowProps {
  label: string;
  values: number[];
  months: string[];
  currentMonth: string;
  tone: "muted" | "emphasized";
}

function SummaryRow({
  label,
  values,
  months,
  currentMonth,
  tone,
}: SummaryRowProps) {
  const toneRow =
    tone === "emphasized"
      ? "border-t border-line-soft bg-panel-2/70 font-medium"
      : "border-t border-line-soft";
  return (
    <tr className={toneRow}>
      <th
        scope="row"
        className="sticky left-0 z-10 bg-panel px-4 py-1.5 text-left text-[12.5px] text-ink"
        style={{ position: "sticky", left: 0, background: tone === "emphasized" ? "hsl(var(--panel-2) / 0.7)" : undefined }}
      >
        {label}
      </th>
      {months.map((m, idx) => {
        const cents = values[idx] ?? 0;
        const isFuture = m > currentMonth;
        const isCurrent = m === currentMonth;
        return (
          <td
            key={m}
            className={cn(
              "relative px-3 py-1.5 text-right font-mono tabular-nums",
              amountClass(cents, isFuture),
            )}
          >
            {isCurrent && (
              <span
                aria-hidden
                className="absolute inset-y-0 left-0 w-0.5 bg-accent"
              />
            )}
            {formatCents(cents)}
          </td>
        );
      })}
    </tr>
  );
}

interface GroupHeaderProps {
  label: string;
  open: boolean;
  onToggle: () => void;
  values: number[];
  months: string[];
  currentMonth: string;
}

function GroupHeaderRow({
  label,
  open,
  onToggle,
  values,
  months,
  currentMonth,
}: GroupHeaderProps) {
  return (
    <tr className="border-t border-line-soft bg-panel-2/50">
      <th
        scope="row"
        className="sticky left-0 z-10 bg-panel-2/50 px-3 py-1.5 text-left"
        style={{ position: "sticky", left: 0 }}
      >
        <button
          type="button"
          onClick={onToggle}
          className="inline-flex items-center gap-1.5 text-[11.5px] font-semibold uppercase tracking-wider text-ink-2 hover:text-ink"
        >
          <Chevron open={open} />
          {label}
        </button>
      </th>
      {months.map((m, idx) => {
        const cents = values[idx] ?? 0;
        const isFuture = m > currentMonth;
        const isCurrent = m === currentMonth;
        return (
          <td
            key={m}
            className={cn(
              "relative px-3 py-1.5 text-right font-mono tabular-nums",
              amountClass(cents, isFuture),
            )}
          >
            {isCurrent && (
              <span
                aria-hidden
                className="absolute inset-y-0 left-0 w-0.5 bg-accent"
              />
            )}
            {formatCents(cents)}
          </td>
        );
      })}
    </tr>
  );
}

interface CategoryRowProps {
  row: PivotRow;
  depth: number;
  hasChildren: boolean;
  expanded: boolean;
  onToggle: () => void;
  onCellClick: (month: string, categoryId: number) => void;
  currentMonth: string;
  isOut?: boolean;
}

function CategoryRow({
  row,
  depth,
  hasChildren,
  expanded,
  onToggle,
  onCellClick,
  currentMonth,
  isOut,
}: CategoryRowProps) {
  return (
    <tr className="border-t border-line-soft last:border-b-0 hover:bg-panel-2/30">
      <th
        scope="row"
        className="sticky left-0 z-10 bg-panel px-3 py-1.5 text-left text-[12.5px] font-normal text-ink"
        style={{ position: "sticky", left: 0, paddingLeft: 12 + depth * 16 }}
      >
        <span className="inline-flex items-center gap-1.5">
          {hasChildren ? (
            <button
              type="button"
              onClick={onToggle}
              className="text-ink-2 hover:text-ink"
              aria-label={expanded ? "Replier" : "Déplier"}
            >
              <Chevron open={expanded} />
            </button>
          ) : (
            <span aria-hidden className="inline-block w-3" />
          )}
          <span className="truncate">{row.label}</span>
        </span>
      </th>
      {row.cells.map((cell) => {
        const isFuture = cell.month > currentMonth;
        const isCurrent = cell.month === currentMonth;
        const clickable = cell.month >= currentMonth;
        const displayed = isOut ? -cell.total_cents : cell.total_cents;
        return (
          <td
            key={cell.month}
            className={cn(
              "relative px-3 py-1.5 text-right font-mono tabular-nums",
              amountClass(displayed, isFuture),
              clickable &&
                "cursor-pointer transition-colors hover:bg-panel-2/50",
            )}
            onClick={
              clickable
                ? () => onCellClick(cell.month, row.category_id)
                : undefined
            }
          >
            {isCurrent && (
              <span
                aria-hidden
                className="absolute inset-y-0 left-0 w-0.5 bg-accent"
              />
            )}
            {formatCents(displayed)}
          </td>
        );
      })}
    </tr>
  );
}

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={cn(
        "h-3 w-3 transition-transform",
        open ? "rotate-90" : "rotate-0",
      )}
    >
      <path d="M9 6l6 6-6 6" />
    </svg>
  );
}
