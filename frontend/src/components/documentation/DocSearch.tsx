import { cn } from "@/lib/utils";

export interface DocSearchProps {
  value: string;
  onChange: (v: string) => void;
  className?: string;
}

/**
 * DocSearch — champ de recherche éditorial pour filtrer les sections documentées.
 *
 * Le filtrage effectif (sur titre, sous-titre et contenu) est géré par le
 * parent : ici on ne s'occupe que de l'input contrôlé et de son style.
 */
export function DocSearch({ value, onChange, className }: DocSearchProps) {
  return (
    <div className={cn("relative", className)}>
      <svg
        aria-hidden
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        className="pointer-events-none absolute left-3 top-1/2 h-[14px] w-[14px] -translate-y-1/2 text-muted-foreground"
      >
        <circle cx="11" cy="11" r="8" />
        <path d="m21 21-4.3-4.3" />
      </svg>
      <input
        type="search"
        role="searchbox"
        aria-label="Rechercher dans la documentation"
        placeholder="Rechercher une page, une feature…"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-md border border-line bg-panel py-2 pl-9 pr-3 text-[13px] text-ink outline-none placeholder:text-muted-foreground focus:border-ink-2"
      />
    </div>
  );
}
