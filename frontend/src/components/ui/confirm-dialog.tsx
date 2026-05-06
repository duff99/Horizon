/**
 * ConfirmDialog — modale de confirmation contrôlée, calée sur le design
 * Horizon (panel + border-line-soft + tipographie 12.5–13.5px).
 *
 * Sert à remplacer les `window.confirm` natifs (alerte navigateur grise,
 * hors du look de l'app, position imprévisible). Préfère cette modale
 * pour toute action destructive ou non triviale.
 *
 * Rendu via React Portal dans `document.body` : indispensable parce que
 * Layout.tsx applique `overflow-x-clip` sur `<main>`, ce qui crée un
 * containing block pour les descendants `position: fixed` (Chrome
 * implémente clip via paint-containment). Sans Portal, la modale serait
 * ancrée au padding du <main> et laisserait une bande blanche en haut.
 */
import { useEffect } from "react";
import { createPortal } from "react-dom";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type ConfirmTone = "default" | "danger";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  /**
   * Description explicative. Une chaîne ou un fragment React (utile pour
   * mettre en avant un nom de catégorie / d'entrée concernée).
   */
  description?: React.ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  /**
   * Ton du bouton de confirmation. `danger` = rouge (suppression,
   * désactivation, action irréversible). `default` = neutre.
   */
  tone?: ConfirmTone;
  /**
   * Quand true, désactive les boutons et passe le label de confirmation
   * en « … » pour signaler une action en cours côté serveur.
   */
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Confirmer",
  cancelLabel = "Annuler",
  tone = "default",
  busy = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !busy) onCancel();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, busy, onCancel]);

  if (!open) return null;
  if (typeof document === "undefined") return null;

  return createPortal(
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-dialog-title"
      className="fixed inset-0 z-[60] flex items-center justify-center px-4"
    >
      <div
        aria-hidden
        onClick={busy ? undefined : onCancel}
        className="absolute inset-0 bg-black/40 backdrop-blur-[2px]"
      />
      <div
        className={cn(
          "relative z-10 w-full max-w-md overflow-hidden rounded-xl border border-line-soft bg-panel shadow-xl",
        )}
      >
        <div className="px-5 py-4">
          <h2
            id="confirm-dialog-title"
            className="text-[15px] font-semibold text-ink"
          >
            {title}
          </h2>
          {description && (
            <div className="mt-2 whitespace-pre-line text-[12.5px] leading-relaxed text-ink-2">
              {description}
            </div>
          )}
        </div>
        <div className="flex items-center justify-end gap-2 border-t border-line-soft bg-panel-2/40 px-5 py-3">
          <Button
            type="button"
            variant="ghost"
            onClick={onCancel}
            disabled={busy}
            className="h-8"
          >
            {cancelLabel}
          </Button>
          <Button
            type="button"
            onClick={onConfirm}
            disabled={busy}
            className={cn(
              "h-8",
              tone === "danger" &&
                "bg-rose-600 text-white hover:bg-rose-700 focus-visible:ring-rose-500",
            )}
          >
            {busy ? "…" : confirmLabel}
          </Button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
