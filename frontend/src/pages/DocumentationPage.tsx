import { useMemo, useState } from "react";

import { DocSearch } from "@/components/documentation/DocSearch";
import { DocSection } from "@/components/documentation/DocSection";
import { DocTOC } from "@/components/documentation/DocTOC";
import { DOC_SECTIONS } from "@/content/documentation";

/**
 * DocumentationPage — guide utilisateur complet de l'application Horizon.
 *
 * Layout éditorial :
 *  - colonne gauche : TOC sticky (lg+) avec surlignage de la section active
 *  - colonne centrale : contenu limité à ~760px pour la lisibilité
 *  - un champ de recherche filtre les sections par titre, sous-titre et contenu
 *
 * Le contenu vit dans `@/content/documentation.ts` pour faciliter la mise à
 * jour éditoriale sans toucher à l'ossature React.
 */
export function DocumentationPage() {
  const [query, setQuery] = useState("");

  const filteredSections = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return DOC_SECTIONS;
    return DOC_SECTIONS.filter((s) => {
      if (s.title.toLowerCase().includes(q)) return true;
      if (s.subtitle.toLowerCase().includes(q)) return true;
      if (s.sees.some((x) => x.toLowerCase().includes(q))) return true;
      if (s.does.some((x) => x.toLowerCase().includes(q))) return true;
      if (s.tips?.some((x) => x.toLowerCase().includes(q))) return true;
      return false;
    });
  }, [query]);

  return (
    <section className="space-y-10">
      <header className="max-w-[65ch]">
        <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-accent">
          <span aria-hidden className="h-px w-8 bg-accent" />
          Guide utilisateur
        </div>
        <h1 className="mt-3 text-[34px] font-semibold tracking-tight text-ink">
          Documentation Horizon
        </h1>
        <p className="mt-3 text-[15px] leading-relaxed text-ink-2">
          Ce guide décrit chaque page de l'application et toutes les actions
          disponibles. Vous y trouverez, pour chaque écran, ce que vous voyez,
          ce que vous pouvez faire, et quelques astuces pour gagner du temps.
        </p>
        <div className="mt-6 max-w-md">
          <DocSearch value={query} onChange={setQuery} />
        </div>
      </header>

      <div className="flex gap-12">
        <DocTOC sections={filteredSections} />

        <div className="min-w-0 flex-1">
          <div className="max-w-[760px] space-y-10">
            {filteredSections.length === 0 ? (
              <div className="rounded-md border border-line-soft bg-panel-2 px-5 py-10 text-center text-[13px] text-muted-foreground">
                Aucune section ne correspond à « {query} ». Essayez un autre
                terme.
              </div>
            ) : (
              filteredSections.map((section) => (
                <DocSection key={section.id} data={section} />
              ))
            )}
          </div>

        </div>
      </div>
    </section>
  );
}
