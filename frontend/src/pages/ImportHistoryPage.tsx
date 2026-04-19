import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchImports } from "../api/imports";
import { Button } from "@/components/ui/button";

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

export function ImportHistoryPage() {
  const { data = [], isLoading } = useQuery({
    queryKey: ["imports"],
    queryFn: fetchImports,
  });

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight text-ink">
            Historique des imports
          </h1>
          <p className="mt-0.5 text-[13px] text-muted-foreground">
            {data.length} import{data.length > 1 ? "s" : ""} effectué{data.length > 1 ? "s" : ""}
          </p>
        </div>
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
                  Statut
                </th>
                <th className="px-3 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Importées
                </th>
                <th className="px-3 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Ignorées
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
                  <td className="px-3 py-3">
                    <span
                      className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[11.5px] font-medium ${
                        STATUS_CLASS[imp.status] ?? "border-line-soft bg-panel-2 text-ink-2"
                      }`}
                    >
                      {STATUS_LABEL[imp.status] ?? imp.status}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-right font-mono text-[13px] tabular-nums text-credit">
                    {imp.imported_count}
                  </td>
                  <td className="px-3 py-3 text-right font-mono text-[13px] tabular-nums text-muted-foreground">
                    {imp.duplicates_skipped}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
