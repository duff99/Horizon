import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { createCounterparty } from "../api/counterparties";

type Props = {
  entityId: number | null;
  onClose: () => void;
  onCreated: () => void;
};

export function CounterpartyCreateDialog({
  entityId,
  onClose,
  onCreated,
}: Props) {
  const [name, setName] = useState("");

  const mut = useMutation({
    mutationFn: () => {
      if (entityId == null) throw new Error("Entité requise");
      return createCounterparty({ entity_id: entityId, name: name.trim() });
    },
    onSuccess: () => onCreated(),
  });

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
    >
      <div
        className="w-[440px] max-w-[90vw] rounded-xl bg-panel p-6 shadow-card"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-[16px] font-semibold text-ink">Nouveau tiers</h2>
        <p className="mt-1 text-[12px] text-muted-foreground">
          Crée manuellement un client ou fournisseur. Utile pour préparer un
          tiers avant le premier import.
        </p>

        {entityId == null && (
          <p className="mt-3 text-[12px] text-amber-700">
            Sélectionne d'abord une entité dans le sélecteur en haut de la page.
          </p>
        )}

        <div className="mt-4">
          <label className="block text-[12px] font-medium text-ink">Nom</label>
          <input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => {
              if (
                e.key === "Enter" &&
                name.trim() &&
                entityId != null &&
                !mut.isPending
              ) {
                mut.mutate();
              }
              if (e.key === "Escape") onClose();
            }}
            className="mt-1 w-full rounded-md border border-line-soft bg-panel px-3 py-2 text-[13px]"
            placeholder="Ex : Carrefour Proxi 75011"
          />
        </div>

        {mut.isError && (
          <p className="mt-3 text-[12px] text-red-600">
            {(mut.error as Error)?.message?.includes("409")
              ? "Un tiers avec ce nom existe déjà."
              : "Échec de la création."}
          </p>
        )}

        <div className="mt-6 flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Annuler
          </Button>
          <Button
            disabled={!name.trim() || entityId == null || mut.isPending}
            onClick={() => mut.mutate()}
          >
            {mut.isPending ? "Création…" : "Créer"}
          </Button>
        </div>
      </div>
    </div>
  );
}
