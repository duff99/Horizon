import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList,
} from "@/components/ui/command";

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
  const selected = value != null ? buildPath(categories, value) : null;

  const grouped = useMemo(() => {
    const roots = categories.filter((c) => c.parent_category_id === null);
    return roots.map((root) => ({
      root,
      children: categories.filter((c) => c.parent_category_id === root.id),
    }));
  }, [categories]);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button role="combobox" variant="outline" className="w-full justify-between">
          {selected ?? (placeholder ?? "Choisir une catégorie")}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[360px] p-0">
        <Command shouldFilter={false}>
          <CommandInput placeholder="Rechercher…" />
          <CommandList>
            <CommandEmpty>Aucune catégorie</CommandEmpty>
            {grouped.map((g) => (
              <CommandGroup key={g.root.id} heading={g.root.name}>
                <CommandItem onSelect={() => { onChange(g.root.id); setOpen(false); }}>
                  {g.root.name}
                </CommandItem>
                {g.children.map((c) => (
                  <CommandItem
                    key={c.id}
                    onSelect={() => { onChange(c.id); setOpen(false); }}
                    className="pl-6"
                  >
                    {c.name}
                  </CommandItem>
                ))}
              </CommandGroup>
            ))}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
