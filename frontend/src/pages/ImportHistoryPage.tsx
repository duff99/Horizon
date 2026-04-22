import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchImports } from "../api/imports";
import { Button } from "@/components/ui/button";
import type { ImportRecord } from "@/types/api";
import { useEntityFilter } from "../stores/entityFilter";
import { EntitySelector } from "@/components/EntitySelector";

const STATUS_LABEL: Record<string, string> = {
  pending: "En cours",
  completed: "Terminé",
  failed: "Échoué",
};

const STATUS_CLASS: Record<string, string> = {
  pending: "bg-amber-100 text-amber-800 border-amber-200",
  completed: "bg-emerald-50 text-emerald-800 border-emerald-200",
  failed: "bg-red-50 text-red-800 border-red-200",
};

const EUR = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 2,
});

function formatEUR(v: string | null): string {
  if (v == null) return "—";
  const n = Number(v);
  return Number.isFinite(n) ? EUR.format(n) : "—";
}

function formatPeriod(start: string | null, end: string | null): string {
  if (!start || !end) return "—";
  const fmt = (d: string) =>
    new Date(d).toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit" });
  return `${fmt(start)} → ${fmt(end)}`;
}

export function ImportHistoryPage() {
  const entityId = useEntityFilter((s) => s.entityId);
  const { data = [], isLoading } = useQuery({
    queryKey: ["imports", entityId],
    queryFn: () => fetchImports({ entityId }),
  });
  const [preview, setPreview] = useState<ImportRecord | null>(null);

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight text-ink">
            Historique des imports
          </h1>
          <p className="mt-0.5 text-[13px] text-muted-foreground">
            {data.length} import{data.length > 1 ? "s" : ""} effectué{data.length > 1 ? "s" : ""}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <EntitySelector />
          <Link to="/imports/nouveau">
          <Button>
            <svg
              aria-hidden
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              className="mr-1.5 h-3.5 w-3.5"
            >
              <path d="M5 12h14M12 5v14" />
            </svg>
            Nouvel import
          </Button>
          </Link>
        </div>
      </div>

      {isLoading ? (
        <div className="rounded-xl border border-line-soft bg-panel p-10 text-center text-[13px] text-muted-foreground shadow-card">
          Chargement…
        </div>
      ) : data.length === 0 ? (
        <div className="rounded-xl border border-line-soft bg-panel p-10 text-center text-[13px] text-muted-foreground shadow-card">
          Aucun import pour le moment. Commencer par{" "}
          <Link to="/imports/nouveau" className="text-accent underline">
            importer un relevé
          </Link>
          .
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-line-soft bg-panel shadow-card">
          <table className="w-full">
            <thead>
              <tr className="border-b border-line-soft bg-panel-2">
                <th className="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Date
                </th>
                <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Fichier
                </th>
                <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Banque
                </th>
                <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Période
                </th>
                <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Statut
                </th>
                <th className="px-3 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Importées
                </th>
                <th className="px-3 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Ignorées
                </th>
                <th className="px-3 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Solde début
                </th>
                <th className="px-3 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Solde fin
                </th>
                <th className="px-3 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {data.map((imp) => (
                <tr
                  key={imp.id}
                  className="border-b border-line-soft transition-colors hover:bg-panel-2"
                >
                  <td className="px-4 py-3 font-mono text-[12.5px] tabular-nums text-ink-2">
                    {imp.created_at
                      ? new Date(imp.created_at).toLocaleDateString("fr-FR")
                      : "—"}
                  </td>
                  <td className="px-3 py-3 text-[13px] text-ink">
                    {imp.filename ?? "—"}
                  </td>
                  <td className="px-3 py-3 text-[12px] font-semibold uppercase tracking-wider text-ink-2">
                    {imp.bank_code}
                  </td>
                  <td className="px-3 py-3 font-mono text-[12.5px] tabular-nums text-ink-2">
                    {formatPeriod(imp.period_start, imp.period_end)}
                  </td>
                  <td className="px-3 py-3">
                    <span
                      className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[11.5px] font-medium ${
                        STATUS_CLASS[imp.status] ?? "border-line-soft bg-panel-2 text-ink-2"
                      }`}
                    >
                      {STATUS_LABEL[imp.status] ?? imp.status}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-right text-[13px] tabular-nums text-ink-2">
                    {imp.imported_count}
                  </td>
                  <td className="px-3 py-3 text-right text-[13px] tabular-nums text-muted-foreground">
                    {imp.duplicates_skipped}
                  </td>
                  <td className="px-3 py-3 text-right font-mono text-[13px] tabular-nums text-ink-2">
                    {formatEUR(imp.opening_balance)}
                  </td>
                  <td className="px-3 py-3 text-right font-mono text-[13px] tabular-nums text-ink">
                    {formatEUR(imp.closing_balance)}
                  </td>
                  <td className="px-3 py-3 text-right">
                    <button
                      type="button"
                      onClick={() => setPreview(imp)}
                      title="Visualiser le PDF"
                      aria-label={`Visualiser ${imp.filename ?? `import ${imp.id}`}`}
                      className="inline-flex h-7 w-7 items-center justify-center rounded-md text-ink-2 transition-colors hover:bg-panel-2 hover:text-ink"
                    >
                      <svg
                        aria-hidden
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth={2}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="h-4 w-4"
                      >
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                        <circle cx="12" cy="12" r="3" />
                      </svg>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {preview && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={`Aperçu de ${preview.filename ?? 'import'}`}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-6"
          onClick={() => setPreview(null)}
        >
          <div
            className="flex h-full w-full max-w-5xl flex-col overflow-hidden rounded-xl bg-panel shadow-card"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-line-soft px-4 py-3">
              <div className="truncate text-[13px] font-medium text-ink">
                {preview.filename ?? `Import #${preview.id}`}
              </div>
              <div className="flex items-center gap-2">
                <a
                  href={`/api/imports/${preview.id}/file`}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-md border border-line px-2.5 py-1 text-[12.5px] text-ink-2 hover:border-ink-2"
                >
                  Ouvrir dans un onglet
                </a>
                <button
                  type="button"
                  onClick={() => setPreview(null)}
                  className="rounded-md border border-line px-2.5 py-1 text-[12.5px] text-ink-2 hover:border-ink-2"
                >
                  Fermer
                </button>
              </div>
            </div>
            <iframe
              title={`PDF ${preview.id}`}
              src={`/api/imports/${preview.id}/file`}
              className="flex-1 w-full bg-white"
            />
          </div>
        </div>
      )}
    </section>
  );
}
