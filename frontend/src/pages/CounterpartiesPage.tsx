import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchCounterparties,
  updateCounterparty,
} from "../api/counterparties";
import { Button } from "@/components/ui/button";
import { useEntityFilter } from "../stores/entityFilter";
import { EntitySelector } from "@/components/EntitySelector";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { CounterpartyMergeDialog } from "@/components/CounterpartyMergeDialog";
import { CounterpartyCreateDialog } from "@/components/CounterpartyCreateDialog";
import type { CounterpartyWithAggregates } from "../types/api";

const fmtEur = (n: number) =>
  new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(n);

const fmtDate = (iso: string | null) =>
  iso ? new Intl.DateTimeFormat("fr-FR").format(new Date(iso)) : "—";

export function CounterpartiesPage() {
  const qc = useQueryClient();
  const entityId = useEntityFilter((s) => s.entityId);
  const [search, setSearch] = useState("");
  const [includeIgnored, setIncludeIgnored] = useState(false);
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [mergeSource, setMergeSource] =
    useState<CounterpartyWithAggregates | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [confirmIgnore, setConfirmIgnore] =
    useState<CounterpartyWithAggregates | null>(null);

  const { data = [], isLoading } = useQuery({
    queryKey: ["counterparties", { entityId, includeIgnored, search }],
    queryFn: () =>
      fetchCounterparties({
        entityId,
        includeIgnored,
        search: search.trim() || undefined,
      }),
  });

  const updateMut = useMutation({
    mutationFn: ({
      id,
      patch,
    }: {
      id: number;
      patch: { status?: "active" | "ignored"; name?: string };
    }) => updateCounterparty(id, patch),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["counterparties"] }),
  });

  const visible = useMemo(() => data, [data]);

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 data-page-title className="text-[22px] font-semibold tracking-tight text-ink">
            Clients & fournisseurs
          </h1>
          <p className="mt-0.5 text-[13px] text-muted-foreground">
            Tiers détectés à partir de tes imports bancaires.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <EntitySelector />
          <Button onClick={() => setCreateOpen(true)}>Nouveau tiers</Button>
        </div>
      </div>

      <div className="rounded-xl border border-line-soft bg-panel-2 p-4 text-[13px] text-muted-foreground">
        <strong className="text-ink">À quoi ça sert.</strong>{" "}
        Cette page liste tous les tiers (clients, fournisseurs, salariés…)
        détectés à partir de tes imports bancaires. Tu peux les renommer,
        fusionner les doublons, et ignorer ceux qui polluent les sélecteurs.
        Pour voir les opérations d'un tiers, clique sur son nom.
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Rechercher un tiers…"
          className="flex-1 min-w-[220px] rounded-md border border-line-soft bg-panel px-3 py-2 text-[13px]"
        />
        <label className="flex items-center gap-2 text-[13px] text-muted-foreground">
          <input
            type="checkbox"
            checked={includeIgnored}
            onChange={(e) => setIncludeIgnored(e.target.checked)}
          />
          Inclure les tiers ignorés
        </label>
      </div>

      {isLoading ? (
        <div className="rounded-xl border border-line-soft bg-panel p-10 text-center text-[13px] text-muted-foreground shadow-card">
          Chargement…
        </div>
      ) : visible.length === 0 ? (
        <div className="rounded-xl border border-line-soft bg-panel p-10 text-center text-[13px] text-muted-foreground shadow-card">
          {search
            ? `Aucun résultat pour "${search}".`
            : "Aucun tiers. Les tiers sont créés automatiquement à chaque import bancaire. Tu peux aussi en créer un manuellement."}
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-line-soft bg-panel shadow-card">
          <table className="w-full">
            <thead>
              <tr className="border-b border-line-soft bg-panel-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                <th className="px-4 py-2.5 text-left">Nom</th>
                <th className="px-4 py-2.5 text-right">Volume cumulé</th>
                <th className="px-4 py-2.5 text-right"># Tx</th>
                <th className="px-4 py-2.5 text-left">Dernière opé</th>
                <th className="px-4 py-2.5 text-right">Engagts en cours</th>
                <th className="px-4 py-2.5 text-left">Statut</th>
                <th className="px-4 py-2.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((cp) => (
                <tr
                  key={cp.id}
                  className="border-b border-line-soft transition-colors hover:bg-panel-2"
                >
                  <td className="px-4 py-3 text-[13px]">
                    {renamingId === cp.id ? (
                      <input
                        autoFocus
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        onBlur={() => {
                          if (
                            renameValue.trim() &&
                            renameValue !== cp.name
                          ) {
                            updateMut.mutate({
                              id: cp.id,
                              patch: { name: renameValue.trim() },
                            });
                          }
                          setRenamingId(null);
                        }}
                        onKeyDown={(e) => {
                          if (e.key === "Enter")
                            (e.target as HTMLInputElement).blur();
                          if (e.key === "Escape") setRenamingId(null);
                        }}
                        className="w-full rounded-md border border-line-soft bg-panel px-2 py-1 text-[13px]"
                      />
                    ) : (
                      <a
                        href={`/transactions?counterparty=${cp.id}`}
                        className="font-medium text-ink hover:underline"
                      >
                        {cp.name}
                      </a>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right text-[13px] tabular-nums">
                    {fmtEur(cp.volume_cumulated)}
                  </td>
                  <td className="px-4 py-3 text-right text-[13px] tabular-nums">
                    {cp.transaction_count}
                  </td>
                  <td className="px-4 py-3 text-[13px] text-muted-foreground">
                    {fmtDate(cp.last_operation_date)}
                  </td>
                  <td className="px-4 py-3 text-right text-[13px] tabular-nums">
                    {cp.pending_commitment_count}
                  </td>
                  <td className="px-4 py-3 text-[13px]">
                    {cp.status === "ignored" ? (
                      <span className="rounded-full bg-amber-50 px-2 py-0.5 text-amber-700 text-[11px]">
                        Ignoré
                      </span>
                    ) : (
                      <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-emerald-700 text-[11px]">
                        Actif
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-1">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          setRenamingId(cp.id);
                          setRenameValue(cp.name);
                        }}
                      >
                        Renommer
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setMergeSource(cp)}
                      >
                        Fusionner…
                      </Button>
                      {cp.status === "ignored" ? (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() =>
                            updateMut.mutate({
                              id: cp.id,
                              patch: { status: "active" },
                            })
                          }
                          title="Réactive ce tiers : il réapparaît dans les sélecteurs et la détection de récurrence."
                        >
                          Réactiver
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setConfirmIgnore(cp)}
                          title="Le tiers reste en base mais disparaît des sélecteurs et des prédictions de récurrence. Pour un tiers récurrent, mieux vaut le renommer."
                        >
                          Ignorer
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {createOpen && (
        <CounterpartyCreateDialog
          entityId={entityId}
          onClose={() => setCreateOpen(false)}
          onCreated={() => {
            qc.invalidateQueries({ queryKey: ["counterparties"] });
            setCreateOpen(false);
          }}
        />
      )}

      {mergeSource && (
        <CounterpartyMergeDialog
          source={mergeSource}
          allCounterparties={visible}
          onClose={() => setMergeSource(null)}
          onMerged={() => {
            qc.invalidateQueries({ queryKey: ["counterparties"] });
            setMergeSource(null);
          }}
        />
      )}

      {confirmIgnore && (
        <ConfirmDialog
          open
          tone="danger"
          title="Ignorer ce tiers ?"
          description={
            `"${confirmIgnore.name}" sera masqué des sélecteurs et exclu des prédictions ` +
            `de récurrence du prévisionnel. Les transactions liées restent visibles. ` +
            `Pour un tiers récurrent, préfère le renommer.`
          }
          confirmLabel="Ignorer"
          onCancel={() => setConfirmIgnore(null)}
          onConfirm={() => {
            updateMut.mutate({
              id: confirmIgnore.id,
              patch: { status: "ignored" },
            });
            setConfirmIgnore(null);
          }}
        />
      )}
    </section>
  );
}
