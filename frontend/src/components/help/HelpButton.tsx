import { HelpCircle } from "lucide-react";
import { useEffect } from "react";
import { useLocation } from "react-router-dom";

import { resolveHelpSection } from "@/lib/help-routes";
import { cn } from "@/lib/utils";

import { HelpDrawer } from "./HelpDrawer";
import { useHelp } from "./HelpProvider";

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  if (target.isContentEditable) return true;
  return false;
}

/**
 * Bouton "Aide" injecté en position fixe (top-right) par Layout.
 *
 * - Masqué sur les routes sans aide (login, documentation, inconnue).
 * - Au clic, ouvre le HelpDrawer avec la section correspondante.
 * - Ferme automatiquement le drawer quand la route change (sinon on resterait
 *   avec une aide sur une page qu'on a quittée).
 * - Le raccourci `?` est attaché ici, pas dans HelpProvider, pour ne pas
 *   armer le toggle sur les pages sans aide (où le drawer ne se monte jamais).
 */
export function HelpButton() {
  const location = useLocation();
  const { isOpen, open, close, toggle } = useHelp();
  const section = resolveHelpSection(location.pathname);

  // Fermer le panneau à la navigation pour éviter d'afficher l'aide d'une autre page.
  useEffect(() => {
    close();
  }, [location.pathname, close]);

  // Raccourci `?` — uniquement quand on a une section à afficher.
  useEffect(() => {
    if (!section) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.key !== "?") return;
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      if (isEditableTarget(e.target)) return;
      e.preventDefault();
      toggle();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [section, toggle]);

  if (!section) return null;

  return (
    <>
      <button
        type="button"
        onClick={toggle}
        aria-expanded={isOpen}
        aria-controls="help-drawer"
        aria-label={`Aide sur cette page (${section.title})`}
        className={cn(
          "fixed right-6 top-6 z-40 inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5",
          "border border-line-soft bg-panel text-[12.5px] font-medium text-ink-2 shadow-card",
          "transition-colors hover:bg-panel-2 hover:text-ink",
        )}
      >
        <HelpCircle className="h-4 w-4" aria-hidden />
        <span>Aide</span>
      </button>
      <HelpDrawer
        section={section}
        isOpen={isOpen}
        onOpenChange={(next) => (next ? open() : close())}
      />
    </>
  );
}
