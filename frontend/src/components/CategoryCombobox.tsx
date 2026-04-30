import { useEffect, useMemo, useRef, useState } from "react";
import { Check, ChevronDown, Search } from "lucide-react";
import { cn } from "@/lib/utils";

export interface CategoryOption {
  id: number;
  name: string;
  slug: string;
  parent_category_id: number | null;
}

interface Props {
  categories: CategoryOption[];
  value: number | null;
  onChange: (id: number | null) => void;
  placeholder?: string;
}

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

export function CategoryCombobox({ categories, value, onChange, placeholder }: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

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
    const roots = categories.filter((c) => c.parent_category_id === null);
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
  }, [categories, query]);

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
          className="absolute left-0 right-0 top-[calc(100%+4px)] z-50 overflow-hidden rounded-md border border-line bg-panel shadow-lg"
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
