/**
 * CategoryDriftDetailModal — modal qui s'ouvre au clic sur une ligne du
 * tableau Dérives par catégorie. Affiche les transactions du mois courant
 * pour la catégorie cliquée, triées par |montant| décroissant.
 *
 * Répond à la question "à cause de quelles transactions exactement ?"
 * quand on voit une dérive forte sur une catégorie.
 */
import { useEffect } from "react";

import { useCategoryDriftDetail } from "@/api/analysis";
import { formatCents } from "@/lib/forecastFormat";

interface Props {
  open: boolean;
  categoryId: number | null;
  entityId: number | undefined;
  onClose: () => void;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

export function CategoryDriftDetailModal({
  open,
  categoryId,
  entityId,
  onClose,
}: Props) {
  const query = useCategoryDriftDetail({
    categoryId: open ? categoryId : null,
    entityId,
  });

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="drift-detail-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="max-h-[80vh] w-full max-w-3xl overflow-hidden rounded-xl border border-line-soft bg-panel shadow-2xl">
        <div className="flex items-start justify-between border-b border-line-soft px-5 py-4">
          <div>
            <h2 id="drift-detail-title" className="text-[16px] font-semibold text-ink">
              {query.data?.category_label ?? "Détails de la dérive"}
            </h2>
            <p className="mt-0.5 text-[12.5px] text-muted-foreground">
              Transactions du mois courant — triées par impact décroissant
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fermer"
            className="rounded-md px-2 py-1 text-[18px] text-muted-foreground hover:bg-panel-2 hover:text-ink"
          >
            ×
          </button>
        </div>

        <div className="max-h-[60vh] overflow-y-auto px-5 py-4">
          {query.isLoading ? (
            <div className="space-y-2">
              <div className="h-6 animate-pulse rounded bg-slate-100" />
              <div className="h-6 animate-pulse rounded bg-slate-100" />
              <div className="h-6 animate-pulse rounded bg-slate-100" />
            </div>
          ) : query.isError ? (
            <div
              role="alert"
              className="rounded-md bg-rose-50 px-3 py-2 text-[12.5px] text-rose-900"
            >
              Impossible de charger le détail des transactions.
            </div>
          ) : !query.data || query.data.transactions.length === 0 ? (
            <div className="py-8 text-center text-[13px] text-muted-foreground">
              Aucune transaction sur le mois courant pour cette catégorie.
            </div>
          ) : (
            <>
              <div className="mb-3 flex items-center justify-between text-[12.5px] text-muted-foreground">
                <span>
                  {query.data.transactions.length} transaction
                  {query.data.transactions.length > 1 ? "s" : ""}
                </span>
                <span>
                  Total :{" "}
                  <span className="font-mono font-semibold tabular-nums text-ink">
                    {formatCents(query.data.total_cents)}
                  </span>
                </span>
              </div>
              <table className="w-full text-[13px]">
                <thead>
                  <tr className="border-b border-line-soft bg-panel-2/50 text-left">
                    <th className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                      Date
                    </th>
                    <th className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                      Tiers / Libellé
                    </th>
                    <th className="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                      Montant
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {query.data.transactions.map((tx) => (
                    <tr
                      key={tx.id}
                      className="border-b border-line-soft last:border-0"
                    >
                      <td className="whitespace-nowrap px-3 py-2 text-ink-2">
                        {formatDate(tx.operation_date)}
                      </td>
                      <td className="px-3 py-2 text-ink">
                        {tx.counterparty ? (
                          <>
                            <div className="font-medium">{tx.counterparty}</div>
                            <div className="text-[11.5px] text-muted-foreground">
                              {tx.label}
                            </div>
                          </>
                        ) : (
                          <span>{tx.label}</span>
                        )}
                      </td>
                      <td
                        className={`whitespace-nowrap px-3 py-2 text-right font-mono tabular-nums ${
                          tx.amount_cents < 0
                            ? "text-rose-700"
                            : "text-emerald-700"
                        }`}
                      >
                        {formatCents(tx.amount_cents)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
