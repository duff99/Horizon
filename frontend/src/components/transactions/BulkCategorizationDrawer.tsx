/**
 * BulkCategorizationDrawer — panneau latéral droit pour catégoriser
 * plusieurs transactions à la fois.
 *
 * S'ouvre automatiquement dès qu'au moins une transaction est sélectionnée.
 * L'utilisateur n'a plus besoin de remonter en haut de la page : il garde
 * sa position dans la liste et agit depuis le panneau de droite, comme
 * pour le panneau d'aide.
 *
 * Pattern aligné sur HelpDrawer (vaul direction="right", 420 px max).
 */
import { X } from "lucide-react";
import { Drawer as DrawerPrimitive } from "vaul";

import { CategoryCombobox } from "@/components/CategoryCombobox";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Category } from "@/types/api";

interface Props {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  selectedCount: number;
  categories: Category[];
  bulkCategoryId: number | null;
  onBulkCategoryChange: (id: number | null) => void;
  onCategorize: () => void;
  onSuggestRule: () => void;
  onDeselectAll: () => void;
  isCategorizing: boolean;
  suggestError: string | null;
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
}: Props) {
  return (
    <DrawerPrimitive.Root
      open={isOpen}
      onOpenChange={onOpenChange}
      direction="right"
      shouldScaleBackground={false}
      // Évite que cliquer hors du drawer désélectionne tout : le drawer ne
      // doit pas être modal pour ne pas masquer la liste de transactions.
      modal={false}
    >
      <DrawerPrimitive.Portal>
        <DrawerPrimitive.Content
          aria-describedby={undefined}
          className={cn(
            "fixed inset-y-0 right-0 z-40 flex h-full w-full max-w-[400px] flex-col bg-panel shadow-xl outline-none",
            "border-l border-line-soft",
          )}
        >
          <DrawerPrimitive.Title className="sr-only">
            Catégorisation en masse
          </DrawerPrimitive.Title>

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
                Choisissez une catégorie puis cliquez sur Catégoriser. Les
                opérations sélectionnées seront mises à jour, la sélection
                vidée et le panneau fermé.
              </p>
              <div className="mt-2">
                <CategoryCombobox
                  categories={categories}
                  value={bulkCategoryId}
                  onChange={onBulkCategoryChange}
                />
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button
                  size="sm"
                  disabled={!bulkCategoryId || isCategorizing}
                  onClick={onCategorize}
                >
                  {isCategorizing ? "Catégorisation…" : "Catégoriser"}
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

          <footer className="border-t border-line-soft bg-panel-2/30 px-5 py-3 text-[11.5px] text-muted-foreground">
            Astuce : sélectionnez plusieurs opérations à la fois (case à
            cocher d'en-tête, ou Maj+clic) pour les catégoriser en une seule
            action.
          </footer>
        </DrawerPrimitive.Content>
      </DrawerPrimitive.Portal>
    </DrawerPrimitive.Root>
  );
}
