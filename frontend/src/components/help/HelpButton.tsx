import { HelpCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useLocation } from "react-router-dom";

import { resolveHelpSection } from "@/lib/help-routes";
import { cn } from "@/lib/utils";

import { HelpDrawer } from "./HelpDrawer";
import { useHelp } from "./HelpProvider";

/** ID du slot DOM dans lequel HelpButton se téléporte. Chaque page peut
 *  placer un `<div id="page-help-slot">` près de son h1 pour héberger le
 *  bouton. Si le slot est absent, le bouton ne s'affiche pas. */
export const PAGE_HELP_SLOT_ID = "page-help-slot";

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  if (target.isContentEditable) return true;
  return false;
}

/**
 * Bouton "Aide" injecté à côté du titre de chaque page via un Portal.
 *
 * - Le HelpButton se rend dans le slot DOM `#page-help-slot` placé par
 *   chaque page à côté de son <h1>. Si le slot est absent (route sans
 *   page-helper, login, etc.), le bouton ne s'affiche pas.
 * - Masqué également sur les routes sans aide (resolveHelpSection nul).
 * - Au clic, ouvre le HelpDrawer avec la section correspondante.
 * - Ferme automatiquement le drawer quand la route change.
 * - Le raccourci `?` est attaché ici (pas dans HelpProvider) pour ne pas
 *   armer le toggle sur les pages sans aide.
 */
export function HelpButton() {
  const location = useLocation();
  const { isOpen, open, close, toggle } = useHelp();
  const section = resolveHelpSection(location.pathname);

  // Le bouton se téléporte dans le <h1 data-page-title> de la page
  // courante. Le h1 peut être monté APRÈS HelpButton (l'Outlet rend la
  // page après le Layout) — on observe le DOM pour récupérer le host
  // dès qu'il apparaît, et on attache un span hôte en fin de h1 pour
  // y portaler le bouton (le bouton apparaît ainsi à côté du titre).
  const [slotEl, setSlotEl] = useState<HTMLElement | null>(null);

  useEffect(() => {
    function attach() {
      const h1 = document.querySelector<HTMLHeadingElement>(
        "h1[data-page-title]",
      );
      if (!h1) {
        setSlotEl(null);
        return;
      }
      let host = h1.querySelector<HTMLSpanElement>(
        "span[data-page-help-host]",
      );
      if (!host) {
        host = document.createElement("span");
        host.dataset.pageHelpHost = "true";
        host.style.display = "inline-flex";
        host.style.alignItems = "center";
        host.style.marginLeft = "0.75rem";
        host.style.verticalAlign = "middle";
        h1.appendChild(host);
      }
      setSlotEl(host);
    }
    attach();
    const obs = new MutationObserver(attach);
    obs.observe(document.body, { childList: true, subtree: true });
    return () => obs.disconnect();
  }, [location.pathname]);

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

  const button = (
    <button
      type="button"
      onClick={toggle}
      aria-expanded={isOpen}
      aria-label={`Aide sur cette page (${section.title})`}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5",
        "border border-line-soft bg-panel text-[12.5px] font-medium text-ink-2 shadow-sm",
        "transition-colors hover:bg-panel-2 hover:text-ink",
      )}
    >
      <HelpCircle className="h-4 w-4" aria-hidden />
      <span>Aide</span>
    </button>
  );

  return (
    <>
      {slotEl ? createPortal(button, slotEl) : null}
      <HelpDrawer
        section={section}
        isOpen={isOpen}
        onOpenChange={(next) => (next ? open() : close())}
      />
    </>
  );
}

/**
 * Slot à placer dans le DOM de chaque page (à côté du h1) pour héberger
 * le bouton Aide. Composant léger : rend juste un div avec l'id attendu.
 *
 * Exemple d'usage :
 *   <div className="flex items-center gap-2">
 *     <h1>Mon titre</h1>
 *     <PageHelpSlot />
 *   </div>
 */
export function PageHelpSlot({ className }: { className?: string }) {
  return <div id={PAGE_HELP_SLOT_ID} className={className} />;
}
