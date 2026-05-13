import { useEffect, useMemo, useRef, useState } from "react";
import { Check, ChevronDown, Search } from "lucide-react";
import { cn } from "@/lib/utils";

export interface CategoryOption {
  id: number;
  name: string;
  slug: string;
  parent_category_id: number | null;
  is_system?: boolean;
}

export type CategoryDirectionHint = "CREDIT" | "DEBIT" | "MIXED";

interface Props {
  categories: CategoryOption[];
  value: number | null;
  onChange: (id: number | null) => void;
  placeholder?: string;
  /**
   * Filtre les catégories proposées selon le sens des transactions concernées :
   * - "CREDIT" (montant > 0) : masque les racines purement décaissement.
   * - "DEBIT" (montant < 0) : masque la racine "Encaissements".
   * - "MIXED" ou undefined : aucune restriction.
   * Les racines "neutres" (Flux financiers, Autres, Non catégorisées) restent
   * toujours visibles car elles peuvent contenir les deux sens.
   */
  directionHint?: CategoryDirectionHint;
}

// Racines toujours visibles (peuvent contenir des credits ET des debits) :
// flux financiers (apports/emprunts/virements), autres, non catégorisées,
// honoraires juridiques (legacy plan 1), flux intergroupe (legacy).
const NEUTRAL_ROOT_SLUGS = new Set([
  "flux-financiers",
  "autres",
  "non-categorisees",
  "honoraires-juridiques",
  "flux-intergroupe",
]);

const CREDIT_ROOT_SLUGS = new Set(["encaissements"]);

function buildPath(cats: CategoryOption[], id: number): string {
  const byId = new Map(cats.map((c) => [c.id, c]));
  const parts: string[] = [];
  let cur: CategoryOption | undefined = byId.get(id);
  while (cur) {
    parts.unshift(cur.name);
    cur = cur.parent_category_id ? byId.get(cur.parent_category_id) : undefined;
  }
  return parts.join(" › ");
}

export function CategoryCombobox({
  categories,
  value,
  onChange,
  placeholder,
  directionHint,
}: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [openUp, setOpenUp] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // À l'ouverture, calcule l'espace disponible sous le trigger : si la
  // dropdown (≈ 320 px) déborderait sous le viewport, on l'ouvre vers le
  // haut. Indispensable dans un Drawer en bas d'écran (vaul) où l'espace
  // sous le champ catégorie est faible.
  useEffect(() => {
    if (!open || !rootRef.current) return;
    const rect = rootRef.current.getBoundingClientRect();
    const spaceBelow = window.innerHeight - rect.bottom;
    const spaceAbove = rect.top;
    setOpenUp(spaceBelow < 320 && spaceAbove > spaceBelow);
  }, [open]);

  const selected = value != null ? buildPath(categories, value) : null;

  // Ferme si on clique en dehors du composant. Implémentation maison pour
  // éviter les conflits de stacking entre Radix Popover et vaul (Drawer
  // non-modal) où le pointerdown était parfois absorbé.
  useEffect(() => {
    if (!open) return;
    const handler = (e: PointerEvent) => {
      const target = e.target as Node | null;
      if (target && rootRef.current && !rootRef.current.contains(target)) {
        setOpen(false);
      }
    };
    document.addEventListener("pointerdown", handler, true);
    return () => document.removeEventListener("pointerdown", handler, true);
  }, [open]);

  useEffect(() => {
    if (open) {
      const t = setTimeout(() => inputRef.current?.focus(), 0);
      return () => clearTimeout(t);
    }
    setQuery("");
  }, [open]);

  const grouped = useMemo(() => {
    const q = query.trim().toLowerCase();
    const match = (name: string) => !q || name.toLowerCase().includes(q);
    const isRootAllowed = (slug: string): boolean => {
      if (!directionHint || directionHint === "MIXED") return true;
      if (NEUTRAL_ROOT_SLUGS.has(slug)) return true;
      const isCreditRoot = CREDIT_ROOT_SLUGS.has(slug);
      if (directionHint === "CREDIT") return isCreditRoot;
      // DEBIT : masque la racine credit-only.
      return !isCreditRoot;
    };
    const roots = categories.filter(
      (c) => c.parent_category_id === null && isRootAllowed(c.slug),
    );
    return roots
      .map((root) => {
        const children = categories.filter((c) => c.parent_category_id === root.id);
        const filteredChildren = children.filter((c) => match(c.name));
        const rootMatches = match(root.name);
        return {
          root,
          rootVisible: rootMatches || filteredChildren.length > 0,
          rootMatches,
          children: rootMatches ? children : filteredChildren,
        };
      })
      .filter((g) => g.rootVisible);
  }, [categories, query, directionHint]);

  function handleSelect(id: number) {
    onChange(id);
    setOpen(false);
  }

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        role="combobox"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "flex h-9 w-full items-center justify-between rounded-md border border-line bg-panel px-3 text-[13px] text-ink",
          "hover:border-ink-2 focus:outline-none focus:ring-2 focus:ring-accent/40",
          !selected && "text-muted-foreground",
        )}
      >
        <span className="truncate">{selected ?? (placeholder ?? "Choisir une catégorie")}</span>
        <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-60" aria-hidden />
      </button>

      {open && (
        <div
          className={cn(
            "absolute left-0 right-0 z-50 overflow-hidden rounded-md border border-line bg-panel shadow-lg",
            openUp
              ? "bottom-[calc(100%+4px)]"
              : "top-[calc(100%+4px)]",
          )}
          role="listbox"
        >
          <div className="flex items-center border-b border-line-soft px-2.5">
            <Search className="mr-2 h-3.5 w-3.5 shrink-0 opacity-50" aria-hidden />
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Rechercher…"
              className="h-9 w-full bg-transparent text-[13px] outline-none placeholder:text-muted-foreground"
            />
          </div>
          <div className="max-h-[280px] overflow-y-auto p-1">
            {grouped.length === 0 ? (
              <div className="px-3 py-6 text-center text-[12.5px] text-muted-foreground">
                Aucune catégorie
              </div>
            ) : (
              grouped.map((g) => (
                <div key={g.root.id} className="py-0.5">
                  <button
                    type="button"
                    onClick={() => handleSelect(g.root.id)}
                    className={cn(
                      "flex w-full cursor-pointer items-center justify-between rounded-sm px-2 py-1.5 text-left text-[13px] font-medium text-ink",
                      "hover:bg-panel-2",
                      value === g.root.id && "bg-accent/15 text-ink",
                    )}
                  >
                    <span className="truncate">{g.root.name}</span>
                    {value === g.root.id && <Check className="h-3.5 w-3.5 text-accent" aria-hidden />}
                  </button>
                  {g.children.map((c) => (
                    <button
                      type="button"
                      key={c.id}
                      onClick={() => handleSelect(c.id)}
                      className={cn(
                        "flex w-full cursor-pointer items-center justify-between rounded-sm px-2 py-1.5 pl-6 text-left text-[13px] text-ink-2",
                        "hover:bg-panel-2 hover:text-ink",
                        value === c.id && "bg-accent/15 text-ink",
                      )}
                    >
                      <span className="truncate">{c.name}</span>
                      {value === c.id && <Check className="h-3.5 w-3.5 text-accent" aria-hidden />}
                    </button>
                  ))}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
