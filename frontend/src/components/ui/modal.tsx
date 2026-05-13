/**
 * Modal — primitif générique pour les boîtes de dialogue de l'app
 * (création/édition d'une entité, saisie d'un champ unique, formulaire
 * complet). Aligné sur le design d'`ConfirmDialog` : panel arrondi,
 * border `line-soft`, fond `panel`, header + body + footer optionnels.
 *
 * À utiliser à la place de :
 *   - `window.prompt` / `window.confirm` (look natif, hors design).
 *   - Drawers `vaul` bottom-sheet quand le contenu est un formulaire
 *     centré (le drawer reste pertinent pour les listes longues type
 *     bottom-sheet mobile).
 *
 * Rendu via React Portal dans `document.body` pour ne pas être ancré
 * dans un containing block parent (cf. raison documentée dans
 * `confirm-dialog.tsx`).
 */
import { useEffect } from "react";
import { createPortal } from "react-dom";

import { cn } from "@/lib/utils";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: React.ReactNode;
  /** Largeur max du panneau. Par défaut `max-w-lg` (≈ 32rem). */
  size?: "sm" | "md" | "lg" | "xl" | "2xl";
  /** Empêche la fermeture (Escape ou clic backdrop). Utile en plein submit. */
  busy?: boolean;
  children: React.ReactNode;
  /** Slot pied de modale (boutons d'action). Optionnel. */
  footer?: React.ReactNode;
}

const SIZE_TO_MAX_W: Record<NonNullable<ModalProps["size"]>, string> = {
  sm: "max-w-sm",
  md: "max-w-md",
  lg: "max-w-lg",
  xl: "max-w-xl",
  "2xl": "max-w-2xl",
};

export function Modal({
  open,
  onClose,
  title,
  description,
  size = "lg",
  busy = false,
  children,
  footer,
}: ModalProps) {
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !busy) onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, busy, onClose]);

  if (!open) return null;
  if (typeof document === "undefined") return null;

  return createPortal(
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      className="fixed inset-0 z-[60] flex items-center justify-center px-4 py-8"
    >
      <div
        aria-hidden
        onClick={busy ? undefined : onClose}
        className="absolute inset-0 bg-black/40 backdrop-blur-[2px]"
      />
      <div
        className={cn(
          "relative z-10 flex w-full flex-col overflow-hidden rounded-xl border border-line-soft bg-panel shadow-xl",
          // 92vh garantit une marge visible en haut et en bas même sur les
          // petits écrans, et active le scroll interne sur le contenu.
          "max-h-[92vh]",
          SIZE_TO_MAX_W[size],
        )}
      >
        <header className="flex items-start justify-between gap-4 border-b border-line-soft px-5 py-4">
          <div className="min-w-0">
            <h2
              id="modal-title"
              className="text-[15px] font-semibold text-ink"
            >
              {title}
            </h2>
            {description && (
              <p className="mt-1 text-[12.5px] leading-relaxed text-ink-2">
                {description}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={busy}
            aria-label="Fermer"
            className="rounded-md p-1 text-ink-2 hover:bg-panel-2 hover:text-ink disabled:cursor-not-allowed disabled:opacity-40"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={1.75}
              strokeLinecap="round"
              strokeLinejoin="round"
              className="h-4 w-4"
            >
              <path d="M6 6l12 12" />
              <path d="M18 6L6 18" />
            </svg>
          </button>
        </header>

        <div className="flex-1 overflow-y-auto px-5 py-4">{children}</div>

        {footer && (
          <footer className="flex flex-wrap items-center justify-end gap-2 border-t border-line-soft bg-panel-2/40 px-5 py-3">
            {footer}
          </footer>
        )}
      </div>
    </div>,
    document.body,
  );
}
