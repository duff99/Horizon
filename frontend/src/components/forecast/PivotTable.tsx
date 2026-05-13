import { useMemo, useRef, useState } from "react";
import type { PivotResult, PivotRow } from "@/types/forecast";
import { formatCents, formatMonthLabel } from "@/lib/forecastFormat";
import { cn } from "@/lib/utils";

interface Props {
  result: PivotResult;
  onCellClick: (
    month: string,
    categoryId: number,
    direction: "in" | "out",
  ) => void;
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

  // ---------------------------------------------------------------------------
  // G8 — What-if overrides
  // clé = `${categoryId}:${month}`, valeur = montant overridé en centimes
  // ---------------------------------------------------------------------------
  const [overrides, setOverrides] = useState<Map<string, number>>(new Map());
  const hasOverrides = overrides.size > 0;

  function getEffective(row: PivotRow, monthIdx: number): number {
    const month = months[monthIdx];
    const key = `${row.category_id}:${month}`;
    return overrides.has(key)
      ? overrides.get(key)!
      : (row.cells[monthIdx]?.total_cents ?? 0);
  }

  function setOverride(categoryId: number, month: string, cents: number) {
    setOverrides((prev) => {
      const next = new Map(prev);
      next.set(`${categoryId}:${month}`, cents);
      return next;
    });
  }

  function clearOverrides() {
    setOverrides(new Map());
  }

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

  // Monthly totals per direction — use effective values (overrides apply)
  const inTotals = useMemo(() => {
    return months.map((_m, idx) =>
      inRows.reduce((s, r) => s + getEffective(r, idx), 0),
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [months, inRows, overrides]);
  const outTotals = useMemo(() => {
    return months.map((_m, idx) =>
      outRows.reduce((s, r) => s + getEffective(r, idx), 0),
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [months, outRows, overrides]);

  // Invariants comptables :
  //   Variation nette[i]  = Encaissements[i] + Décaissements[i] (signés)
  //                         + Net non-catégorisé[i]
  //   Tréso fin[i]        = Tréso début[i] + Variation nette[i]
  //   Tréso début[i+1]    = Tréso fin[i]
  //
  // Sans `uncategorized_net_cents`, la trésorerie de fin de mois divergeait
  // de la réalité bancaire (les tx sans catégorie sont dans le solde
  // mais pas dans les `rows`).
  const uncatByMonth = useMemo(
    () => months.map((_m, i) => result.uncategorized_net_cents?.[i] ?? 0),
    [months, result.uncategorized_net_cents],
  );

  const netByMonth = useMemo(
    () =>
      months.map(
        (_m, i) => inTotals[i] + outTotals[i] + uncatByMonth[i],
      ),
    [months, inTotals, outTotals, uncatByMonth],
  );

  // Tréso fin de mois calculée de proche en proche depuis le solde
  // d'ouverture global. C'est la SEULE source de vérité du tableau, qu'il
  // y ait des overrides ou non — garantit la continuité opening[i+1] = closing[i].
  const closingByMonth = useMemo(() => {
    const arr: number[] = [];
    for (let i = 0; i < months.length; i++) {
      const opening = i === 0 ? result.opening_balance_cents : (arr[i - 1] ?? 0);
      arr.push(opening + netByMonth[i]);
    }
    return arr;
  }, [months, result.opening_balance_cents, netByMonth]);

  // Tréso début de mois : strictement la clôture du mois précédent (ou
  // l'ouverture globale pour le premier). Continuité garantie par
  // construction.
  const openingByMonth = useMemo(() => {
    const arr: number[] = [];
    for (let i = 0; i < months.length; i++) {
      arr.push(i === 0 ? result.opening_balance_cents : closingByMonth[i - 1]);
    }
    return arr;
  }, [months, result.opening_balance_cents, closingByMonth]);

  return (
    <div className="overflow-x-auto rounded-xl border border-line-soft bg-panel shadow-card">
      {/* G8 — Bandeau avertissement mode simulation */}
      {hasOverrides && (
        <div className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-[12.5px] text-amber-900">
          Mode simulation actif — les valeurs modifiées (fond orange) sont locales à votre
          navigateur et ne sont pas enregistrées. Cliquez sur{" "}
          <button
            type="button"
            onClick={clearOverrides}
            className="font-semibold underline underline-offset-2"
          >
            Réinitialiser
          </button>{" "}
          pour revenir aux données réelles.
        </div>
      )}
      <table className="min-w-full border-collapse text-[12.5px]">
        <thead>
          <tr className="border-b border-line-soft bg-panel-2">
            <th
              className="sticky left-0 z-20 min-w-[260px] bg-panel-2 px-4 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground"
              style={{ position: "sticky", left: 0 }}
            >
              <div className="flex items-center justify-between">
                <span>Catégorie</span>
                {/* G8 — Bouton Réinitialiser */}
                {hasOverrides && (
                  <button
                    type="button"
                    onClick={clearOverrides}
                    title="Remet toutes les cellules à leurs valeurs réelles du scénario actif."
                    className="ml-2 rounded bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-900 hover:bg-amber-200"
                  >
                    Réinitialiser les simulations
                  </button>
                )}
              </div>
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
              overrides={overrides}
              onOverride={setOverride}
            />
          ))}

          {/* Décaissements group */}
          <GroupHeaderRow
            label="Décaissements"
            open={outGroupOpen}
            onToggle={() => setOutGroupOpen((v) => !v)}
            values={outTotals}
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
              overrides={overrides}
              onOverride={setOverride}
            />
          ))}

          {/* Net non-catégorisé — affiché uniquement si non-nul, indispensable
              pour expliquer un éventuel écart visible dans le tableau. */}
          {uncatByMonth.some((v) => v !== 0) && (
            <SummaryRow
              label="Tx non catégorisées (net)"
              values={uncatByMonth}
              months={months}
              currentMonth={currentMonth}
              tone="muted"
            />
          )}

          {/* Net variation */}
          <SummaryRow
            label="Variation nette de cash"
            values={netByMonth}
            months={months}
            currentMonth={currentMonth}
            tone="emphasized"
          />

          {/* Trésorerie fin de mois — toujours calculée de proche en proche
              pour garantir la continuité opening[i+1] = closing[i]. */}
          <SummaryRow
            label={hasOverrides ? "Trésorerie en fin de mois (simulation)" : "Trésorerie en fin de mois"}
            values={closingByMonth}
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
              "relative whitespace-nowrap px-3 py-1.5 text-right font-mono tabular-nums",
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
              "relative whitespace-nowrap px-3 py-1.5 text-right font-mono tabular-nums",
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
  onCellClick: (
    month: string,
    categoryId: number,
    direction: "in" | "out",
  ) => void;
  currentMonth: string;
  isOut?: boolean;
  // G8
  overrides: Map<string, number>;
  onOverride: (categoryId: number, month: string, cents: number) => void;
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
  overrides,
  onOverride,
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
        const overrideKey = `${row.category_id}:${cell.month}`;
        const isOverridden = overrides.has(overrideKey);
        const effectiveCents = isOverridden
          ? overrides.get(overrideKey)!
          : cell.total_cents;
        // Convention comptable signée : encaissements positifs (vert),
        // décaissements négatifs (rouge). On affiche la valeur brute du
        // backend, qui est déjà signée (négative pour les sorties).
        const displayed = effectiveCents;

        return (
          <WhatIfCell
            key={cell.month}
            month={cell.month}
            displayed={displayed}
            isOverridden={isOverridden}
            isFuture={isFuture}
            isCurrent={isCurrent}
            clickable={clickable}
            isOut={isOut}
            signAnomaly={cell.sign_anomaly === true}
            onCellClick={() =>
              onCellClick(cell.month, row.category_id, isOut ? "out" : "in")
            }
            onOverride={(euros) => {
              // Convention signée : l'utilisateur saisit la valeur telle
              // qu'elle s'affiche (positive pour un encaissement, négative
              // pour un décaissement). On la stocke comme telle.
              const cents = Math.round(euros * 100);
              onOverride(row.category_id, cell.month, cents);
            }}
          />
        );
      })}
    </tr>
  );
}

// ---------------------------------------------------------------------------
// G8 — Cellule what-if avec double-clic pour édition
// ---------------------------------------------------------------------------

interface WhatIfCellProps {
  month: string; // utilisé pour la key, pas dans le rendu
  displayed: number;
  isOverridden: boolean;
  isFuture: boolean;
  isCurrent: boolean;
  clickable: boolean;
  isOut?: boolean;
  signAnomaly?: boolean;
  onCellClick: () => void;
  onOverride: (euros: number) => void;
}

function WhatIfCell({
  month: _month,
  displayed,
  isOverridden,
  isFuture,
  isCurrent,
  clickable,
  signAnomaly,
  onCellClick,
  onOverride,
}: WhatIfCellProps) {
  const [editing, setEditing] = useState(false);
  const [inputVal, setInputVal] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  function startEdit(e: React.MouseEvent) {
    // Double-clic sur mois futur uniquement
    if (!clickable) return;
    e.stopPropagation();
    // Convention signée : on pré-remplit avec la valeur telle qu'affichée
    // (négative pour un décaissement). L'utilisateur peut taper un signe
    // négatif pour saisir un décaissement.
    setInputVal(String(displayed / 100));
    setEditing(true);
    // Focus après render
    setTimeout(() => inputRef.current?.focus(), 0);
  }

  function commitEdit() {
    const val = parseFloat(inputVal);
    if (!isNaN(val)) {
      onOverride(val);
    }
    setEditing(false);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      commitEdit();
    } else if (e.key === "Escape") {
      setEditing(false);
    }
  }

  return (
    <td
      className={cn(
        "relative whitespace-nowrap px-3 py-1.5 text-right font-mono tabular-nums",
        isOverridden
          ? "bg-amber-50 text-amber-900"
          : amountClass(displayed, isFuture),
        clickable && !editing && "cursor-pointer transition-colors hover:bg-panel-2/50",
      )}
      onClick={!editing && clickable ? onCellClick : undefined}
      onDoubleClick={clickable ? startEdit : undefined}
      title={clickable ? "Double-clic pour simuler un montant (what-if)" : undefined}
    >
      {isCurrent && (
        <span
          aria-hidden
          className="absolute inset-y-0 left-0 w-0.5 bg-accent"
        />
      )}
      {signAnomaly && !editing && (
        <span
          aria-label="Signe inattendu : cette cellule mélange entrées et sorties"
          title="Signe inattendu : une transaction de signe opposé au kind de la catégorie est présente sur ce mois. Vérifie la classification de la tx ou le kind de la catégorie."
          className="absolute left-1 top-1 select-none text-[10px] leading-none text-amber-600"
        >
          ⚠
        </span>
      )}
      {editing ? (
        <input
          ref={inputRef}
          type="number"
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          onBlur={commitEdit}
          onKeyDown={handleKeyDown}
          className="w-full bg-amber-50 border border-amber-300 rounded px-1 text-right font-mono text-[13px] text-amber-900 focus:outline-none"
          onClick={(e) => e.stopPropagation()}
        />
      ) : (
        formatCents(displayed)
      )}
    </td>
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
