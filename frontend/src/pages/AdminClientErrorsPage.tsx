/**
 * Page /administration/erreurs-client — Erreurs client JavaScript.
 *
 * Liste paginée des erreurs JavaScript remontées automatiquement par les
 * navigateurs des utilisateurs. Filtres : gravité, statut (acquitté ou non),
 * période. Action d'acquittement ligne par ligne.
 *
 * Accessible uniquement via AdminRoute. Concept nouveau : bandeau d'introduction
 * permanent, tooltip sur l'action d'acquittement.
 */
import { useState } from "react";

import {
  useClientErrors,
  useAcknowledgeClientError,
  type ClientErrorFilters,
} from "@/api/clientErrors";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const PAGE_SIZE = 50;

function formatDateTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString("fr-FR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function truncate(s: string, n = 80): string {
  if (s.length <= n) return s;
  return s.slice(0, n - 1) + "…";
}

function severityBadgeClass(severity: string): string {
  if (severity === "fatal")
    return "bg-rose-100 text-rose-900 border border-rose-200";
  if (severity === "error")
    return "bg-red-50 text-red-800 border border-red-200";
  if (severity === "warning")
    return "bg-amber-50 text-amber-800 border border-amber-200";
  return "bg-slate-100 text-slate-700 border border-slate-200";
}

export function AdminClientErrorsPage() {
  const [severity, setSeverity] = useState<string>("__all__");
  const [acknowledgedFilter, setAcknowledgedFilter] = useState<string>("__all__");
  const [since, setSince] = useState("");
  const [until, setUntil] = useState("");
  const [offset, setOffset] = useState(0);

  const filters: ClientErrorFilters = {
    limit: PAGE_SIZE,
    offset,
  };
  if (severity !== "__all__") filters.severity = severity;
  if (acknowledgedFilter === "false") filters.acknowledged = false;
  if (acknowledgedFilter === "true") filters.acknowledged = true;
  if (since) filters.since = since;
  if (until) filters.until = until;

  const query = useClientErrors(filters);
  const ackMut = useAcknowledgeClientError();
  const items = query.data?.items ?? [];
  const total = query.data?.total ?? 0;
  const pageCount = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  function handleFilterChange() {
    setOffset(0);
  }

  return (
    <section className="space-y-6">
      {/* En-tête */}
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight text-ink">
          Erreurs client
        </h1>
        <p className="mt-0.5 text-[13px] text-muted-foreground">
          Erreurs JavaScript remontées automatiquement par les navigateurs des
          utilisateurs.
        </p>
      </div>

      {/* Bandeau d'introduction permanent — concept nouveau */}
      <div
        role="note"
        className="rounded-md border border-blue-200 bg-blue-50 px-4 py-3 text-[13px] text-blue-900"
      >
        Cette page liste les erreurs JavaScript survenues dans le navigateur des
        utilisateurs. Chaque entrée correspond à une exception non interceptée,
        un appel API échoué ou une erreur remontée manuellement. Acquittez une
        erreur une fois qu'elle a été examinée et traitée — cela ne la supprime
        pas.
      </div>

      {/* Barre de filtres */}
      <div className="flex flex-wrap items-end gap-3">
        {/* Gravité */}
        <div className="space-y-1">
          <label className="text-[11.5px] font-medium text-ink-2">
            Gravité
          </label>
          <Select
            value={severity}
            onValueChange={(v) => {
              setSeverity(v);
              handleFilterChange();
            }}
          >
            <SelectTrigger className="w-[140px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">Toutes</SelectItem>
              <SelectItem value="fatal">Fatal</SelectItem>
              <SelectItem value="error">Error</SelectItem>
              <SelectItem value="warning">Warning</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Statut acquittement */}
        <div className="space-y-1">
          <label className="text-[11.5px] font-medium text-ink-2">Statut</label>
          <Select
            value={acknowledgedFilter}
            onValueChange={(v) => {
              setAcknowledgedFilter(v);
              handleFilterChange();
            }}
          >
            <SelectTrigger className="w-[200px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">Toutes</SelectItem>
              <SelectItem value="false">Non acquittees uniquement</SelectItem>
              <SelectItem value="true">Acquittees uniquement</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Depuis */}
        <div className="space-y-1">
          <label className="text-[11.5px] font-medium text-ink-2">Depuis</label>
          <input
            type="date"
            value={since}
            onChange={(e) => {
              setSince(e.target.value);
              handleFilterChange();
            }}
            className="rounded-md border border-line bg-panel px-2.5 py-1.5 text-[12.5px] text-ink outline-none focus:border-ink-2"
          />
        </div>

        {/* Jusqu'au */}
        <div className="space-y-1">
          <label className="text-[11.5px] font-medium text-ink-2">
            Jusqu'au
          </label>
          <input
            type="date"
            value={until}
            onChange={(e) => {
              setUntil(e.target.value);
              handleFilterChange();
            }}
            className="rounded-md border border-line bg-panel px-2.5 py-1.5 text-[12.5px] text-ink outline-none focus:border-ink-2"
          />
        </div>
      </div>

      {/* Etat chargement / erreur */}
      {query.isLoading ? (
        <div className="rounded-xl border border-line-soft bg-panel p-10 text-center text-[13px] text-muted-foreground shadow-card">
          Chargement…
        </div>
      ) : query.isError ? (
        <div
          role="alert"
          className="rounded-md bg-rose-50 px-4 py-3 text-[13px] text-rose-900"
        >
          Impossible de charger les erreurs client.
        </div>
      ) : (
        <>
          {/* Tableau */}
          <div className="overflow-hidden rounded-xl border border-line-soft bg-panel shadow-card">
            <table className="w-full text-[12.5px]">
              <thead>
                <tr className="border-b border-line-soft bg-panel-2">
                  <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    ID
                  </th>
                  <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Date
                  </th>
                  <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Utilisateur
                  </th>
                  <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Gravite
                  </th>
                  <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Message
                  </th>
                  <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    URL
                  </th>
                  <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Statut
                  </th>
                  <th className="px-3 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line-soft">
                {items.length === 0 ? (
                  <tr>
                    <td
                      colSpan={8}
                      className="px-5 py-10 text-center text-[13px] text-muted-foreground"
                    >
                      Aucune erreur ne correspond aux filtres.
                    </td>
                  </tr>
                ) : (
                  items.map((item) => (
                    <tr
                      key={item.id}
                      className="transition-colors hover:bg-panel-2"
                    >
                      <td className="px-3 py-3 font-mono text-[11.5px] text-muted-foreground">
                        {item.id}
                      </td>
                      <td className="px-3 py-3 text-ink-2 whitespace-nowrap">
                        {formatDateTime(item.occurred_at)}
                      </td>
                      <td className="px-3 py-3 text-ink-2">
                        {item.user_email ?? "Anonyme"}
                      </td>
                      <td className="px-3 py-3">
                        <span
                          className={
                            "inline-flex rounded-md px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wider " +
                            severityBadgeClass(item.severity)
                          }
                        >
                          {item.severity}
                        </span>
                      </td>
                      <td
                        className="px-3 py-3 text-ink max-w-[280px] truncate"
                        title={item.message}
                      >
                        {truncate(item.message)}
                      </td>
                      <td
                        className="px-3 py-3 text-ink-2 max-w-[180px] truncate font-mono text-[11px]"
                        title={item.url ?? ""}
                      >
                        {item.url ? truncate(item.url, 40) : "—"}
                      </td>
                      <td className="px-3 py-3">
                        {item.acknowledged_at ? (
                          <span className="inline-flex rounded-md bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-800 border border-emerald-200">
                            Acquitte
                          </span>
                        ) : (
                          <span className="inline-flex rounded-md bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-800 border border-amber-200">
                            A traiter
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-3 text-right">
                        {!item.acknowledged_at && (
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={ackMut.isPending}
                            onClick={() => ackMut.mutate(item.id)}
                            title="Indique que cette erreur a ete examinee et traitee. Ne supprime pas l'entree."
                          >
                            Marquer acquitte
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {pageCount > 1 && (
            <div className="flex items-center justify-between text-[12.5px] text-muted-foreground">
              <span>
                {total} erreur{total > 1 ? "s" : ""} · Page {currentPage} sur{" "}
                {pageCount}
              </span>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                >
                  Precedent
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={offset + PAGE_SIZE >= total}
                  onClick={() => setOffset(offset + PAGE_SIZE)}
                >
                  Suivant
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}
