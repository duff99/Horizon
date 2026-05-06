/**
 * BulkCategorizationDrawer — panneau latéral droit pour catégoriser
 * plusieurs transactions à la fois.
 *
 * S'ouvre automatiquement dès qu'au moins une transaction est sélectionnée.
 * Implémentation en div fixe (sans vaul) : vaul installait des handlers
 * pointerdown qui interféraient avec la propagation des clics vers la
 * liste de transactions (re-clic checkbox bloqué, popovers internes qui
 * ne se fermaient pas). Avec un panneau plain HTML, plus aucun conflit.
 *
 * Rendu via `createPortal` directement dans `document.body` : le `<main>`
 * de Layout utilise `overflow-x-clip`, que Chrome implémente en
 * paint-containment, ce qui crée un containing block pour les descendants
 * `position: fixed`. Sans le portail, le drawer se positionnerait par
 * rapport au `<main>` (qui commence sous le `py-6` du wrapper) et laisserait
 * une bande blanche en haut. En passant par `document.body` on garantit
 * que `top:0` réfère bien au viewport.
 */
import { createPortal } from "react-dom";

import { X } from "lucide-react";

import {
  CategoryCombobox,
  type CategoryDirectionHint,
  type CategoryOption,
} from "@/components/CategoryCombobox";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface Props {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  selectedCount: number;
  categories: CategoryOption[];
  bulkCategoryId: number | null;
  onBulkCategoryChange: (id: number | null) => void;
  onCategorize: () => void;
  onSuggestRule: () => void;
  onDeselectAll: () => void;
  isCategorizing: boolean;
  suggestError: string | null;
  /**
   * Sens cumulé des transactions sélectionnées (calculé depuis le signe des
   * montants par TransactionsPage). Sert à filtrer les catégories proposées :
   * un encaissement (montant > 0) ne peut pas tomber dans une catégorie de
   * décaissement, et inversement.
   */
  directionHint?: CategoryDirectionHint;
}

export function BulkCategorizationDrawer({
  isOpen,
  onOpenChange,
  selectedCount,
  categories,
  bulkCategoryId,
  onBulkCategoryChange,
  onCategorize,
  onSuggestRule,
  onDeselectAll,
  isCategorizing,
  suggestError,
  directionHint,
}: Props) {
  const directionLabel =
    directionHint === "CREDIT"
      ? "Encaissements uniquement"
      : directionHint === "DEBIT"
        ? "Décaissements uniquement"
        : directionHint === "MIXED"
          ? "Sélection mixte (encaissements + décaissements)"
          : null;
  if (typeof document === "undefined") return null;
  return createPortal(
    <>
      {/* Backdrop semi-transparent : clic = fermeture. Animé en opacité
          pour ne pas brutaliser la transition latérale du panneau. */}
      <div
        aria-hidden
        onClick={() => onOpenChange(false)}
        className={cn(
          "fixed inset-0 z-40 bg-black/30 transition-opacity duration-200",
          isOpen ? "opacity-100" : "pointer-events-none opacity-0",
        )}
      />
      <aside
        aria-hidden={!isOpen}
        aria-label="Catégorisation en masse"
        className={cn(
          // `inset-y-0` (top:0 + bottom:0) impose la hauteur via les bords
          // au lieu d'un `h-dvh` calculé : pas de dépendance au support
          // dynamic-viewport-height (Safari ancien, certaines versions
          // Firefox), donc plus de risque que le footer se retrouve clippé
          // sous le bord bas, ni de bande blanche au-dessus quand la
          // hauteur n'était pas correctement résolue.
          "fixed inset-y-0 right-0 z-50 flex w-full max-w-[400px] flex-col border-l border-line-soft bg-panel shadow-xl",
          "transition-transform duration-200 ease-out",
          isOpen ? "translate-x-0" : "pointer-events-none translate-x-full",
        )}
      >
        <header className="flex items-start justify-between gap-2 border-b border-line-soft px-5 py-4">
        <div>
          <div className="text-[15px] font-semibold text-ink">
            Catégoriser la sélection
          </div>
          <div className="mt-0.5 text-[12.5px] text-muted-foreground">
            {selectedCount} opération{selectedCount > 1 ? "s" : ""}{" "}
            sélectionnée{selectedCount > 1 ? "s" : ""}
          </div>
        </div>
        <button
          type="button"
          onClick={() => onOpenChange(false)}
          aria-label="Fermer le panneau de catégorisation"
          className="rounded-md p-1.5 text-ink-2 transition-colors hover:bg-panel-2 hover:text-ink"
        >
          <X className="h-4 w-4" aria-hidden />
        </button>
      </header>

      <div className="flex-1 space-y-5 overflow-y-auto px-5 py-5">
        <section>
          <label
            htmlFor="bulk-cat-combobox"
            className="block text-[12.5px] font-medium text-ink-2"
          >
            Catégorie à appliquer
          </label>
          <p className="mt-0.5 text-[11.5px] text-muted-foreground">
            Choisissez une catégorie puis cliquez sur Appliquer. Les
            opérations sélectionnées seront mises à jour, la sélection
            vidée et le panneau fermé.
          </p>
          {directionLabel && (
            <p
              className={cn(
                "mt-1.5 inline-flex items-center gap-1 rounded-sm px-1.5 py-0.5 text-[11px] font-medium",
                directionHint === "CREDIT" &&
                  "bg-emerald-50 text-emerald-800",
                directionHint === "DEBIT" && "bg-rose-50 text-rose-800",
                directionHint === "MIXED" && "bg-amber-50 text-amber-800",
              )}
            >
              {directionLabel}
            </p>
          )}
          <div className="mt-2">
            <CategoryCombobox
              categories={categories}
              value={bulkCategoryId}
              onChange={onBulkCategoryChange}
              directionHint={directionHint}
            />
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button
              size="sm"
              disabled={!bulkCategoryId || isCategorizing}
              onClick={onCategorize}
            >
              {isCategorizing ? "Application…" : "Appliquer"}
            </Button>
            <Button size="sm" variant="ghost" onClick={onDeselectAll}>
              Désélectionner tout
            </Button>
          </div>
        </section>

        <section className="rounded-md border border-line-soft bg-panel-2/40 p-4">
          <div className="text-[13px] font-medium text-ink">
            Automatiser pour les prochaines fois
          </div>
          <p className="mt-1 text-[11.5px] leading-relaxed text-muted-foreground">
            Si les opérations sélectionnées partagent un libellé
            commun, vous pouvez créer une règle de catégorisation
            automatique pour qu'elles soient traitées seules dès le
            prochain import.
          </p>
          <div className="mt-3">
            <Button
              size="sm"
              variant="outline"
              onClick={onSuggestRule}
              disabled={selectedCount === 0}
            >
              Suggérer une règle
            </Button>
          </div>
          {suggestError && (
            <div
              role="alert"
              className="mt-3 rounded-md border border-rose-200 bg-rose-50 px-2.5 py-1.5 text-[11.5px] text-rose-900"
            >
              {suggestError}
            </div>
          )}
        </section>
      </div>

      <footer className="shrink-0 border-t border-line-soft bg-panel-2/30 px-5 py-3 text-[11.5px] text-muted-foreground">
        Astuce : sélectionnez plusieurs opérations à la fois (case à
        cocher d'en-tête, ou Maj+clic) pour les catégoriser en une seule
        action.
      </footer>
    </aside>
    </>,
    document.body,
  );
}
