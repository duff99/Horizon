import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { fetchMergePreview, executeMerge } from "../api/counterparties";
import type { CounterpartyWithAggregates, MergePreview } from "../types/api";

type Props = {
  source: CounterpartyWithAggregates;
  allCounterparties: CounterpartyWithAggregates[];
  onClose: () => void;
  onMerged: () => void;
};

const fmtEur = (n: number) =>
  new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(n);

export function CounterpartyMergeDialog({
  source,
  allCounterparties,
  onClose,
  onMerged,
}: Props) {
  const [targetId, setTargetId] = useState<number | null>(null);

  const candidates = allCounterparties.filter(
    (cp) => cp.id !== source.id && cp.entity_id === source.entity_id,
  );

  const previewQ = useQuery<MergePreview>({
    queryKey: ["merge-preview", source.id, targetId],
    queryFn: () => fetchMergePreview(source.id, targetId!),
    enabled: targetId != null,
  });

  const mergeMut = useMutation({
    mutationFn: () => executeMerge(source.id, targetId!),
    onSuccess: () => onMerged(),
  });

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
    >
      <div
        className="w-[560px] max-w-[90vw] rounded-xl bg-panel p-6 shadow-card"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-[16px] font-semibold text-ink">
          Fusionner « {source.name} » vers…
        </h2>
        <p className="mt-1 text-[12px] text-muted-foreground">
          Toutes les transactions, engagements, règles et lignes de
          prévisionnel seront réattachés au tiers cible. Le tiers source
          sera supprimé.
          <strong className="text-ink"> Action irréversible.</strong>
        </p>

        <div className="mt-4">
          <label className="block text-[12px] font-medium text-ink">
            Tiers cible
          </label>
          <select
            value={targetId ?? ""}
            onChange={(e) =>
              setTargetId(e.target.value ? Number(e.target.value) : null)
            }
            className="mt-1 w-full rounded-md border border-line-soft bg-panel px-3 py-2 text-[13px]"
          >
            <option value="">— Choisir —</option>
            {candidates.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.transaction_count} tx)
              </option>
            ))}
          </select>
        </div>

        {targetId != null && previewQ.data && (
          <div className="mt-4 rounded-md border border-line-soft bg-panel-2 p-3 text-[13px]">
            <p className="font-medium text-ink">Récapitulatif :</p>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-muted-foreground">
              <li>
                {previewQ.data.transaction_count} transaction(s) réattachée(s)
              </li>
              <li>
                {previewQ.data.commitments.length} engagement(s) réattaché(s)
              </li>
              <li>
                {previewQ.data.rules.length} règle(s) de catégorisation
                mise(s) à jour
              </li>
            </ul>
            {previewQ.data.commitments.length > 0 && (
              <details className="mt-3">
                <summary className="cursor-pointer text-[12px] text-ink">
                  Détail des engagements
                </summary>
                <ul className="mt-2 space-y-1 text-[12px] text-muted-foreground">
                  {previewQ.data.commitments.map((c) => (
                    <li key={c.id}>
                      #{c.id} ·{" "}
                      {c.direction === "in" ? "à encaisser" : "à payer"}{" "}
                      {fmtEur(c.amount)} · prévu {c.expected_date}
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        )}

        {mergeMut.isError && (
          <p className="mt-3 text-[12px] text-red-600">
            Échec de la fusion. Réessaie ou vérifie les permissions.
          </p>
        )}

        <div className="mt-6 flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Annuler
          </Button>
          <Button
            disabled={
              targetId == null || previewQ.isLoading || mergeMut.isPending
            }
            onClick={() => mergeMut.mutate()}
          >
            {mergeMut.isPending ? "Fusion en cours…" : "Confirmer la fusion"}
          </Button>
        </div>
      </div>
    </div>
  );
}
