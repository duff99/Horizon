import { X } from "lucide-react";
import { Drawer as DrawerPrimitive } from "vaul";

import type { DocSectionData } from "@/content/documentation";
import { cn } from "@/lib/utils";

import { HelpContent } from "./HelpContent";

interface HelpDrawerProps {
  section: DocSectionData | null;
  isOpen: boolean;
  onOpenChange: (next: boolean) => void;
}

/**
 * Panneau d'aide latéral droit.
 *
 * - Glissé depuis la droite via Vaul `direction="right"`.
 * - 420px sur desktop, full-width sous 640px.
 * - `shouldScaleBackground={false}` car le scaling iOS de Vaul est conçu pour
 *   les bottom sheets, pas pour un panneau latéral.
 */
export function HelpDrawer({ section, isOpen, onOpenChange }: HelpDrawerProps) {
  if (!section) return null;

  return (
    <DrawerPrimitive.Root
      open={isOpen}
      onOpenChange={onOpenChange}
      direction="right"
      shouldScaleBackground={false}
    >
      <DrawerPrimitive.Portal>
        <DrawerPrimitive.Overlay
          className={cn("fixed inset-0 z-50 bg-black/50")}
        />
        <DrawerPrimitive.Content
          aria-describedby={undefined}
          className={cn(
            "fixed inset-y-0 right-0 z-50 flex h-full w-full max-w-[420px] flex-col bg-panel shadow-xl outline-none",
            "border-l border-line-soft",
          )}
        >
          <DrawerPrimitive.Title className="sr-only" aria-hidden>
            Aide — {section.title}
          </DrawerPrimitive.Title>
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            aria-label="Fermer l'aide"
            className={cn(
              "absolute right-3 top-3 rounded-md p-1.5 text-ink-2 transition-colors",
              "hover:bg-panel-2 hover:text-ink",
            )}
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
          <HelpContent section={section} />
        </DrawerPrimitive.Content>
      </DrawerPrimitive.Portal>
    </DrawerPrimitive.Root>
  );
}
