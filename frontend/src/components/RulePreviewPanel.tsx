import type { RulePreviewResponse } from "@/api/rules";

const EUR = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 2,
});

const DATE = new Intl.DateTimeFormat("fr-FR", {
  day: "2-digit",
  month: "short",
  year: "2-digit",
});

function formatDate(iso: string): string {
  try {
    return DATE.format(new Date(iso));
  } catch {
    return iso;
  }
}

export function RulePreviewPanel({ preview }: { preview: RulePreviewResponse | null }) {
  if (!preview) return null;

  const { matching_count, sample } = preview;
  const shownCount = sample.length;
  const hasMore = matching_count > shownCount;

  return (
    <div className="mt-4 rounded-md border border-line-soft bg-panel-2/50">
      <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-line-soft px-3 py-2">
        <span className="text-[13px] font-semibold text-ink">
          {matching_count.toLocaleString("fr-FR")} transaction
          {matching_count > 1 ? "s" : ""} correspond
          {matching_count > 1 ? "ent" : ""} à cette règle
        </span>
        {shownCount > 0 && (
          <span className="text-[11.5px] text-muted-foreground">
            {hasMore
              ? `Aperçu des ${shownCount} plus récentes`
              : `Aperçu complet (${shownCount})`}
          </span>
        )}
      </div>

      {matching_count === 0 ? (
        <div className="px-3 py-6 text-center text-[12.5px] text-muted-foreground">
          Aucune transaction ne correspond pour l'instant. Si la règle est
          appliquée, elle ne touchera rien tant qu'aucun nouvel import n'arrive.
        </div>
      ) : (
        <div className="max-h-[260px] overflow-y-auto">
          <table className="w-full text-[12.5px]">
            <thead className="sticky top-0 bg-panel-2 text-[10.5px] font-semibold uppercase tracking-wider text-muted-foreground">
              <tr className="border-b border-line-soft">
                <th className="px-3 py-1.5 text-left">Date</th>
                <th className="px-3 py-1.5 text-left">Libellé</th>
                <th className="px-3 py-1.5 text-right">Montant</th>
              </tr>
            </thead>
            <tbody>
              {sample.map((s) => {
                const amount = parseFloat(s.amount);
                return (
                  <tr
                    key={s.id}
                    className="border-b border-line-soft/60 last:border-0"
                  >
                    <td className="whitespace-nowrap px-3 py-1.5 text-muted-foreground mono">
                      {formatDate(s.operation_date)}
                    </td>
                    <td className="px-3 py-1.5 text-ink">
                      <div className="line-clamp-2 break-words" title={s.label}>
                        {s.label}
                      </div>
                    </td>
                    <td
                      className={
                        "whitespace-nowrap px-3 py-1.5 text-right font-medium mono " +
                        (amount < 0 ? "text-debit" : "text-credit")
                      }
                    >
                      {amount >= 0 ? "+" : ""}
                      {EUR.format(amount)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
