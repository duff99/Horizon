/**
 * GhostCommitmentsBanner — bandeau jaune affiché en tête de la liste
 * des engagements quand au moins un engagement est "fantôme" (en retard
 * de plus de 7 jours sans transaction associée).
 *
 * Deux actions :
 *  - "Voir la liste" : transmet à la page un signal pour filtrer la
 *    liste affichée aux seuls fantômes (callback onShowPhantomsOnly).
 *  - "Tout clôturer" : ouvre une ConfirmDialog, puis appelle
 *    bulkCancelCommitments avec les ids fantômes calculés côté front.
 */
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import {
  useBulkCancelCommitments,
  useCommitmentKpis,
  useCommitments,
  type CommitmentDirection,
} from "../api/commitments";

type Props = {
  entityId: number | null;
  direction?: CommitmentDirection;
  onShowPhantomsOnly: () => void;
};

export function GhostCommitmentsBanner({
  entityId,
  direction,
  onShowPhantomsOnly,
}: Props) {
  const kpis = useCommitmentKpis({ entityId, direction });
  const phantomCount =
    (kpis.data?.in?.phantom_count ?? 0) + (kpis.data?.out?.phantom_count ?? 0);

  const all = useCommitments({
    entityId,
    status: "pending",
    direction,
    perPage: 500,
  });

  const phantomIds = useMemo(() => {
    const cutoff = new Date();
    cutoff.setHours(0, 0, 0, 0);
    cutoff.setDate(cutoff.getDate() - 7);
    return (all.data?.items ?? [])
      .filter(
        (c) =>
          !c.matched_transaction_id && new Date(c.expected_date) < cutoff,
      )
      .map((c) => c.id);
  }, [all.data]);

  const cancelMut = useBulkCancelCommitments();
  const [confirmOpen, setConfirmOpen] = useState(false);

  if (!phantomCount) return null;

  return (
    <>
      <div className="flex flex-wrap items-start justify-between gap-4 rounded-xl border border-amber-200 bg-amber-50 p-4 text-[13px] text-amber-900">
        <div className="min-w-[260px] flex-1 leading-relaxed">
          <strong>
            {phantomCount} engagement{phantomCount > 1 ? "s" : ""} probablement
            fantôme{phantomCount > 1 ? "s" : ""}.
          </strong>{" "}
          Ces lignes en retard de plus de 7 jours sans transaction associée
          gonflent peut-être ton prévisionnel à tort.
        </div>
        <div className="flex shrink-0 gap-2">
          <Button variant="ghost" size="sm" onClick={onShowPhantomsOnly}>
            Voir la liste
          </Button>
          <Button
            size="sm"
            onClick={() => setConfirmOpen(true)}
            disabled={phantomIds.length === 0}
            title="Marque tous ces engagements comme annulés. Ils sortent du prévisionnel et des indicateurs DSO/DPO. Réversible ligne par ligne via Réactiver."
          >
            Tout clôturer
          </Button>
        </div>
      </div>

      <ConfirmDialog
        open={confirmOpen}
        tone="danger"
        title={`Clôturer ${phantomIds.length} engagement${phantomIds.length > 1 ? "s" : ""} fantôme${phantomIds.length > 1 ? "s" : ""} ?`}
        description={
          "Ils seront marqués comme annulés et sortiront du prévisionnel " +
          "et des indicateurs DSO/DPO. Action réversible ligne par ligne " +
          "via Réactiver."
        }
        confirmLabel="Clôturer"
        busy={cancelMut.isPending}
        onCancel={() => {
          if (!cancelMut.isPending) setConfirmOpen(false);
        }}
        onConfirm={() => {
          cancelMut.mutate(phantomIds, {
            onSuccess: () => setConfirmOpen(false),
          });
        }}
      />
    </>
  );
}
