import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchImports } from "../api/imports";

const STATUS_LABEL: Record<string, string> = {
  pending: "En cours",
  completed: "Terminé",
  failed: "Échoué",
};

export function ImportHistoryPage() {
  const { data = [], isLoading } = useQuery({
    queryKey: ["imports"],
    queryFn: fetchImports,
  });

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Historique des imports</h1>
        <Link
          to="/imports/nouveau"
          className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground"
        >
          Nouvel import
        </Link>
      </div>

      {isLoading && <p>Chargement…</p>}

      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left">
            <th className="py-2">Date</th>
            <th>Fichier</th>
            <th>Banque</th>
            <th>Statut</th>
            <th className="text-right">Importées</th>
            <th className="text-right">Ignorées</th>
          </tr>
        </thead>
        <tbody>
          {data.map((imp) => (
            <tr key={imp.id} className="border-b">
              <td className="py-2">
                {imp.created_at
                  ? new Date(imp.created_at).toLocaleDateString("fr-FR")
                  : "—"}
              </td>
              <td>{imp.filename ?? "—"}</td>
              <td className="uppercase">{imp.bank_code}</td>
              <td>{STATUS_LABEL[imp.status] ?? imp.status}</td>
              <td className="text-right">{imp.imported_count}</td>
              <td className="text-right">{imp.duplicates_skipped}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {!isLoading && data.length === 0 && (
        <p className="text-sm text-muted-foreground">
          Aucun import pour le moment. Commencer par{" "}
          <Link to="/imports/nouveau" className="underline">
            importer un relevé
          </Link>
          .
        </p>
      )}
    </div>
  );
}
