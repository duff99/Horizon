/**
 * ExportButton — bouton générique pour déclencher un export CSV (G11).
 *
 * Usage :
 *   <ExportButton url="/api/transactions/export?entity_id=1" filename="transactions_2026-05-07.csv" />
 *
 * Le bouton affiche un état de chargement pendant le téléchargement et
 * un message d'erreur inline si l'export échoue.
 */
import { useState } from "react";
import { downloadExport } from "@/api/exports";

interface ExportButtonProps {
  /** URL relative backend (avec query params déjà inclus). */
  url: string;
  /** Nom de fichier suggéré pour le téléchargement. */
  filename: string;
  /** Label optionnel du bouton (défaut : "Exporter CSV"). */
  label?: string;
  /** Classes CSS additionnelles. */
  className?: string;
}

export function ExportButton({
  url,
  filename,
  label = "Exporter CSV",
  className = "",
}: ExportButtonProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    setLoading(true);
    setError(null);
    try {
      await downloadExport(url, filename);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue lors de l'export");
    } finally {
      setLoading(false);
    }
  }

  return (
    <span className="inline-flex flex-col items-end gap-1">
      <button
        type="button"
        onClick={handleClick}
        disabled={loading}
        title="Telecharge les donnees affichees au format CSV (separateur point-virgule, encodage UTF-8 avec BOM pour Excel)."
        className={[
          "inline-flex items-center gap-1.5 rounded-md border border-line-soft bg-panel px-3 py-1.5",
          "text-[12px] font-medium text-ink-2 transition-colors hover:border-ink-2 hover:bg-panel-2",
          "disabled:cursor-wait disabled:opacity-60",
          className,
        ]
          .filter(Boolean)
          .join(" ")}
      >
        {loading ? (
          <>
            <svg
              aria-hidden
              className="h-3.5 w-3.5 animate-spin text-muted-foreground"
              viewBox="0 0 24 24"
              fill="none"
            >
              <circle
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="3"
                className="opacity-25"
              />
              <path
                fill="currentColor"
                className="opacity-75"
                d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
              />
            </svg>
            Export en cours…
          </>
        ) : (
          <>
            <svg
              aria-hidden
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              className="h-3.5 w-3.5 shrink-0"
            >
              <path d="M12 5v14M5 12l7 7 7-7" />
            </svg>
            {label}
          </>
        )}
      </button>
      {error && (
        <span className="text-[11px] text-red-600" role="alert">
          {error}
        </span>
      )}
    </span>
  );
}
