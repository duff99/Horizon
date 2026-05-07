import { useQuery } from "@tanstack/react-query";
import { fetchRecurringSuggestions } from "@/api/forecast";
import type { DetectedRecurrenceSuggestion } from "@/api/forecast";
import { formatCents } from "@/lib/forecastFormat";
import { cn } from "@/lib/utils";

interface Props {
  entityId: number;
  onSelect: (suggestion: DetectedRecurrenceSuggestion) => void;
  onClose: () => void;
}

const RECURRENCE_LABELS: Record<string, string> = {
  MONTHLY: "Mensuel",
  WEEKLY: "Hebdomadaire",
  QUARTERLY: "Trimestriel",
  YEARLY: "Annuel",
  NONE: "Ponctuel",
};

export function RecurringSuggestionPicker({ entityId, onSelect, onClose }: Props) {
  const query = useQuery({
    queryKey: ["recurring-suggestions", entityId],
    queryFn: () => fetchRecurringSuggestions(entityId),
    staleTime: 5 * 60 * 1000, // 5 min — l'historique ne change pas à chaque ouverture
  });

  return (
    <div className="rounded-lg border border-line-soft bg-panel-2/60 p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-[12px] font-semibold text-ink">
          Récurrences détectées sur 6 mois
        </span>
        <button
          type="button"
          onClick={onClose}
          className="text-[11px] text-muted-foreground hover:text-ink"
        >
          Fermer
        </button>
      </div>

      {query.isLoading && (
        <div className="py-3 text-center text-[12px] text-muted-foreground">
          Analyse en cours…
        </div>
      )}
      {query.isError && (
        <div className="rounded-md bg-rose-50 px-2 py-1.5 text-[12px] text-rose-800">
          Impossible d'analyser l'historique.
        </div>
      )}
      {query.data && query.data.length === 0 && (
        <div className="py-3 text-center text-[12px] text-muted-foreground">
          Aucune récurrence détectée sur les 6 derniers mois.
        </div>
      )}
      {query.data && query.data.length > 0 && (
        <ul className="max-h-48 space-y-1 overflow-y-auto">
          {query.data.slice(0, 10).map((s, i) => {
            const cents = Math.round(Number(s.average_amount) * 100);
            return (
              <li key={i}>
                <button
                  type="button"
                  onClick={() => onSelect(s)}
                  className={cn(
                    "flex w-full items-center justify-between gap-2 rounded-md border",
                    "border-line-soft bg-panel px-3 py-2 text-left text-[12px]",
                    "transition-colors hover:border-accent hover:bg-accent/5",
                  )}
                >
                  <span className="min-w-0 flex-1 truncate font-medium text-ink">
                    {s.counterparty_name}
                  </span>
                  <span className="shrink-0 text-[11px] text-muted-foreground">
                    {RECURRENCE_LABELS[s.recurrence] ?? s.recurrence}
                  </span>
                  <span
                    className={cn(
                      "shrink-0 font-mono text-[12px] tabular-nums",
                      cents >= 0 ? "text-emerald-700" : "text-rose-700",
                    )}
                  >
                    {formatCents(cents)}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
