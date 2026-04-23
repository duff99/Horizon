import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";
import type { DocSectionData } from "@/content/documentation";

export interface DocTOCProps {
  sections: DocSectionData[];
}

/**
 * DocTOC — table des matières sticky avec surlignage de la section visible.
 *
 * Utilise un IntersectionObserver pour détecter la section active pendant le
 * scroll. L'observer est neutralisé pendant les tests (`!('IntersectionObserver'
 * in window)` → fallback sur la première section).
 */
export function DocTOC({ sections }: DocTOCProps) {
  const [activeId, setActiveId] = useState<string>(
    sections[0]?.id ?? "",
  );

  useEffect(() => {
    if (typeof window === "undefined" || !("IntersectionObserver" in window)) {
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        // Garde la première section dont le top est au-dessus de la ligne de
        // déclenchement (40% du viewport depuis le haut).
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]?.target.id) {
          setActiveId(visible[0].target.id);
        }
      },
      {
        rootMargin: "-40% 0px -55% 0px",
        threshold: [0, 1],
      },
    );

    const nodes = sections
      .map((s) => document.getElementById(s.id))
      .filter((n): n is HTMLElement => !!n);
    nodes.forEach((n) => observer.observe(n));

    return () => observer.disconnect();
  }, [sections]);

  return (
    <nav
      aria-label="Table des matières"
      className="sticky top-6 hidden w-[240px] shrink-0 self-start lg:block"
    >
      <div className="mb-3 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
        Sommaire
      </div>
      <ol className="space-y-0.5 border-l border-line-soft">
        {sections.map((s, idx) => {
          const active = s.id === activeId;
          return (
            <li key={s.id}>
              <a
                href={`#${s.id}`}
                data-active={active || undefined}
                className={cn(
                  "group relative -ml-px flex items-center gap-2 border-l-2 py-1.5 pl-3 pr-2 text-[13px] leading-snug transition-colors",
                  active
                    ? "border-accent text-ink"
                    : "border-transparent text-muted-foreground hover:border-line hover:text-ink-2",
                )}
              >
                <span
                  aria-hidden
                  className={cn(
                    "w-5 shrink-0 text-right font-mono text-[10.5px] tabular-nums",
                    active ? "text-accent" : "text-muted-foreground/60",
                  )}
                >
                  {String(idx + 1).padStart(2, "0")}
                </span>
                <span className="truncate">{s.title}</span>
              </a>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
