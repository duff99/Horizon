/**
 * Pagination — composant réutilisable pour listes paginées.
 *
 * Inclut :
 *  - Boutons « / ‹ / › / »  (premier, précédent, suivant, dernier)
 *  - Numéros de page cliquables avec ellipsis intelligente
 *    (1 … 4 5 [6] 7 8 … 25 si le total est grand)
 *  - Champ "Aller à la page __" (validation par Entrée)
 *  - Sélecteur "Lignes par page" (25 / 50 / 100 / 200)
 *  - Récapitulatif "Affichage X à Y sur N · Page P sur T"
 *
 * Convention : page commence à 1 (1-indexed), comme côté backend.
 */
import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";

export const PAGE_SIZE_OPTIONS = [25, 50, 100, 200] as const;
export type PageSize = (typeof PAGE_SIZE_OPTIONS)[number];

interface Props {
  page: number;
  perPage: number;
  total: number;
  onPageChange: (page: number) => void;
  onPerPageChange?: (perPage: PageSize) => void;
}

/**
 * Calcule la liste des numéros à afficher avec ellipsis.
 *
 * Stratégie classique : on garde toujours la 1ère, la dernière, et un
 * voisinage de ±2 autour de la page courante. Les sauts sont remplacés
 * par "…". Exemples (current, total) :
 *   (1, 5)   → 1 2 3 4 5
 *   (3, 10)  → 1 2 3 4 5 … 10
 *   (7, 20)  → 1 … 5 6 7 8 9 … 20
 *   (20, 20) → 1 … 16 17 18 19 20
 */
function buildPageList(current: number, total: number): (number | "ellipsis")[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }
  const out: (number | "ellipsis")[] = [];
  const left = Math.max(2, current - 2);
  const right = Math.min(total - 1, current + 2);

  out.push(1);
  if (left > 2) out.push("ellipsis");
  for (let p = left; p <= right; p++) out.push(p);
  if (right < total - 1) out.push("ellipsis");
  out.push(total);
  return out;
}

export function Pagination({
  page,
  perPage,
  total,
  onPageChange,
  onPerPageChange,
}: Props) {
  const totalPages = Math.max(1, Math.ceil(total / perPage));
  const safePage = Math.min(Math.max(1, page), totalPages);
  const firstItem = total === 0 ? 0 : (safePage - 1) * perPage + 1;
  const lastItem = Math.min(safePage * perPage, total);

  const pages = buildPageList(safePage, totalPages);

  const [jumpInput, setJumpInput] = useState("");
  // Reset le champ Aller à si on change de page d'une autre manière
  useEffect(() => {
    setJumpInput("");
  }, [safePage]);

  function handleJump() {
    const n = parseInt(jumpInput, 10);
    if (Number.isInteger(n) && n >= 1 && n <= totalPages) {
      onPageChange(n);
    }
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line-soft bg-panel-2 px-5 py-3 text-[12.5px] text-muted-foreground">
      <div>
        Affichage{" "}
        <span className="font-medium text-ink-2">
          {firstItem.toLocaleString("fr-FR")}
        </span>{" "}
        à{" "}
        <span className="font-medium text-ink-2">
          {lastItem.toLocaleString("fr-FR")}
        </span>{" "}
        sur{" "}
        <span className="font-medium text-ink-2">
          {total.toLocaleString("fr-FR")}
        </span>
        {" · "}
        Page{" "}
        <span className="font-medium text-ink-2">{safePage}</span>{" "}
        sur{" "}
        <span className="font-medium text-ink-2">{totalPages}</span>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {onPerPageChange && (
          <label className="flex items-center gap-1.5">
            <span>Lignes :</span>
            <select
              value={perPage}
              onChange={(e) => {
                const next = Number(e.target.value) as PageSize;
                // Un seul appel — le caller gère page=1 dans le même
                // setFilters pour éviter une race entre deux setState
                // consécutifs (closure React qui écrase l'un l'autre).
                onPerPageChange(next);
              }}
              className="rounded-sm border border-line-soft bg-panel px-2 py-1 text-[12.5px] text-ink hover:bg-panel-2"
            >
              {PAGE_SIZE_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
        )}

        <div className="flex items-center gap-0.5">
          <NavBtn
            label="«"
            title="Première page"
            disabled={safePage <= 1}
            onClick={() => onPageChange(1)}
          />
          <NavBtn
            label="‹"
            title="Page précédente"
            disabled={safePage <= 1}
            onClick={() => onPageChange(safePage - 1)}
          />

          {pages.map((p, i) =>
            p === "ellipsis" ? (
              <span
                key={`e-${i}`}
                aria-hidden
                className="px-1.5 text-muted-foreground"
              >
                …
              </span>
            ) : (
              <button
                key={p}
                type="button"
                onClick={() => onPageChange(p)}
                aria-current={p === safePage ? "page" : undefined}
                className={cn(
                  "min-w-[28px] rounded-sm border px-2 py-1 text-[12.5px] tabular-nums transition-colors",
                  p === safePage
                    ? "border-accent bg-accent/10 font-semibold text-accent"
                    : "border-line-soft bg-panel text-ink-2 hover:bg-panel-2",
                )}
              >
                {p}
              </button>
            ),
          )}

          <NavBtn
            label="›"
            title="Page suivante"
            disabled={safePage >= totalPages}
            onClick={() => onPageChange(safePage + 1)}
          />
          <NavBtn
            label="»"
            title="Dernière page"
            disabled={safePage >= totalPages}
            onClick={() => onPageChange(totalPages)}
          />
        </div>

        {totalPages > 5 && (
          <label className="flex items-center gap-1.5">
            <span>Aller à :</span>
            <input
              type="number"
              min={1}
              max={totalPages}
              value={jumpInput}
              onChange={(e) => setJumpInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleJump();
              }}
              placeholder={String(safePage)}
              className="w-[70px] rounded-sm border border-line-soft bg-panel px-2 py-1 text-[12.5px] text-ink"
              aria-label="Aller à la page"
            />
          </label>
        )}
      </div>
    </div>
  );
}

function NavBtn({
  label,
  title,
  disabled,
  onClick,
}: {
  label: string;
  title: string;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      aria-label={title}
      className={cn(
        "min-w-[28px] rounded-sm border border-line-soft bg-panel px-2 py-1 text-[13px] text-ink-2 transition-colors hover:bg-panel-2",
        disabled && "cursor-not-allowed opacity-40 hover:bg-panel",
      )}
    >
      {label}
    </button>
  );
}
