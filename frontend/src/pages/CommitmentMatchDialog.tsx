// TODO(v2): ajouter une recherche libre de transactions en complément des
// suggestions automatiques du backend (filtre par libellé/montant/date).
import { useEffect, useState } from "react";

import { ApiError } from "@/api/client";
import {
  useMatchCommitment,
  useSuggestMatches,
  type CommitmentTransactionBrief,
} from "@/api/commitments";
import { Button } from "@/components/ui/button";

type Props = {
  commitmentId: number | null;
  onClose: () => void;
};

const EUR = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 2,
});

function formatAmount(amount: string): string {
  const n = Number(amount);
  return Number.isFinite(n) ? EUR.format(n) : amount;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("fr-FR");
}

export function CommitmentMatchDialog({ commitmentId, onClose }: Props) {
  const open = commitmentId != null;
  const { data, isLoading } = useSuggestMatches(commitmentId);
  const matchMut = useMatchCommitment();
  const [serverError, setServerError] = useState<string | null>(null);
  const [linkingId, setLinkingId] = useState<number | null>(null);

  useEffect(() => {
    if (!open) {
      setServerError(null);
      setLinkingId(null);
    }
  }, [open]);

  if (!open || commitmentId == null) return null;

  const candidates: CommitmentTransactionBrief[] = data?.candidates ?? [];

  async function handleLink(tx: CommitmentTransactionBrief) {
    if (commitmentId == null) return;
    setServerError(null);
    setLinkingId(tx.id);
    try {
      await matchMut.mutateAsync({
        id: commitmentId,
        transaction_id: tx.id,
      });
      onClose();
    } catch (err) {
      if (err instanceof ApiError) {
        setServerError(err.detail || "Erreur inconnue");
      } else {
        setServerError("Erreur inconnue");
      }
    } finally {
      setLinkingId(null);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="commitment-match-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-[640px] rounded-xl border border-line-soft bg-panel p-6 shadow-card">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2
              id="commitment-match-title"
              className="text-[16px] font-semibold text-ink"
            >
              Apparier à une transaction
            </h2>
            <p className="mt-0.5 text-[12.5px] text-muted-foreground">
              Sélectionnez une transaction candidate pour marquer cet
              engagement comme payé.
            </p>
          </div>
        </div>

        <div className="mt-4">
          {isLoading ? (
            <div className="p-6 text-center text-[13px] text-muted-foreground">
              Recherche de candidats…
            </div>
          ) : candidates.length === 0 ? (
            <div className="rounded-md border border-line-soft bg-panel-2 p-6 text-center text-[13px] text-muted-foreground">
              Aucune transaction candidate trouvée.
            </div>
          ) : (
            <ul className="divide-y divide-line-soft rounded-md border border-line-soft bg-panel-2">
              {candidates.map((tx) => (
                <li
                  key={tx.id}
                  className="flex items-center gap-3 px-3 py-2.5"
                >
                  <div className="w-[84px] shrink-0 font-mono text-[12.5px] tabular-nums text-ink-2">
                    {formatDate(tx.operation_date)}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-[13px] text-ink">
                      {tx.label}
                    </div>
                    {tx.bank_account_label && (
                      <div className="truncate text-[11.5px] text-muted-foreground">
                        {tx.bank_account_label}
                      </div>
                    )}
                  </div>
                  <div
                    className={
                      "w-[110px] shrink-0 text-right font-mono text-[13px] tabular-nums " +
                      (Number(tx.amount) < 0 ? "text-debit" : "text-credit")
                    }
                  >
                    {formatAmount(tx.amount)}
                  </div>
                  <button
                    type="button"
                    onClick={() => handleLink(tx)}
                    disabled={linkingId === tx.id}
                    className="shrink-0 rounded-md border border-line px-2.5 py-1 text-[11.5px] text-ink-2 hover:border-ink-2 hover:text-ink disabled:opacity-60"
                  >
                    {linkingId === tx.id ? "Liaison…" : "Lier"}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {serverError && (
          <div
            role="alert"
            className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-[12.5px] text-red-800"
          >
            {serverError}
          </div>
        )}

        <div className="mt-4 flex justify-end">
          <Button type="button" variant="ghost" onClick={onClose}>
            Fermer
          </Button>
        </div>
      </div>
    </div>
  );
}
