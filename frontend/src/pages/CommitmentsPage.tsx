import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { EntitySelector } from "@/components/EntitySelector";
import { GhostCommitmentsBanner } from "@/components/GhostCommitmentsBanner";
import { cn } from "@/lib/utils";
import { useEntityFilter } from "../stores/entityFilter";
import {
  useCancelCommitment,
  useCommitments,
  useCommitmentKpis,
  useUpdateCommitment,
  type Commitment,
  type CommitmentDirection,
  type CommitmentDirectionKpis,
  type CommitmentStatus,
} from "../api/commitments";
import { CommitmentFormDialog } from "./CommitmentFormDialog";
import { CommitmentMatchDialog } from "./CommitmentMatchDialog";

type Tab = "in" | "out" | "all";

const EUR = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 2,
});

const EUR0 = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});

function formatCents(cents: number, direction: CommitmentDirection): string {
  const signed = direction === "out" ? -cents : cents;
  return EUR.format(signed / 100);
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("fr-FR");
}

function startOfToday(): Date {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d;
}

function isOverdue(c: Commitment): boolean {
  return c.status === "pending" && new Date(c.expected_date) < startOfToday();
}

function isPhantom(c: Commitment): boolean {
  if (c.status !== "pending" || c.matched_transaction_id) return false;
  const cutoff = startOfToday();
  cutoff.setDate(cutoff.getDate() - 7);
  return new Date(c.expected_date) < cutoff;
}

const TABS: { value: Tab; label: string }[] = [
  { value: "in", label: "À encaisser" },
  { value: "out", label: "À payer" },
  { value: "all", label: "Tout" },
];

function StatusBadge({ status }: { status: CommitmentStatus }) {
  const styles: Record<CommitmentStatus, string> = {
    pending: "border-amber-200 bg-amber-50 text-amber-800",
    paid: "border-emerald-200 bg-emerald-50 text-emerald-800",
    cancelled: "border-slate-200 bg-slate-50 text-slate-600",
  };
  const labels: Record<CommitmentStatus, string> = {
    pending: "En attente",
    paid: "Payé",
    cancelled: "Annulé",
  };
  return (
    <span
      className={
        "inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium " +
        styles[status]
      }
    >
      {labels[status]}
    </span>
  );
}

function OverdueBadge() {
  return (
    <span className="inline-flex items-center rounded-full border border-red-200 bg-red-50 px-2 py-0.5 text-[11px] font-semibold text-red-700">
      En retard
    </span>
  );
}

function DirectionPill({ direction }: { direction: CommitmentDirection }) {
  const styles =
    direction === "in"
      ? "border-emerald-200 bg-emerald-50 text-emerald-800"
      : "border-rose-200 bg-rose-50 text-rose-800";
  const label = direction === "in" ? "À encaisser" : "À payer";
  return (
    <span
      className={
        "inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium " +
        styles
      }
    >
      {label}
    </span>
  );
}

function KpiCard({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string;
  tone?: "neutral" | "warn";
}) {
  return (
    <div
      className={cn(
        "rounded-xl border p-4 shadow-card",
        tone === "warn"
          ? "border-amber-200 bg-amber-50"
          : "border-line-soft bg-panel",
      )}
    >
      <div className="text-[11px] uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div
        className={cn(
          "mt-1 text-[18px] font-semibold tabular-nums",
          tone === "warn" ? "text-amber-900" : "text-ink",
        )}
      >
        {value}
      </div>
    </div>
  );
}

function DirectionKpiTriad({
  title,
  kpis,
}: {
  title: string;
  kpis: CommitmentDirectionKpis | undefined;
}) {
  const data = kpis ?? {
    total_30d_cents: 0,
    overdue_total_cents: 0,
    overdue_count: 0,
    phantom_count: 0,
  };
  return (
    <div className="space-y-2">
      <div className="text-[11.5px] font-semibold uppercase tracking-wider text-muted-foreground">
        {title}
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <KpiCard
          label="Sous 30 jours"
          value={EUR0.format(data.total_30d_cents / 100)}
        />
        <KpiCard
          label="En retard (montant)"
          value={EUR0.format(data.overdue_total_cents / 100)}
          tone={data.overdue_total_cents > 0 ? "warn" : "neutral"}
        />
        <KpiCard
          label="En retard (nombre)"
          value={String(data.overdue_count)}
          tone={data.overdue_count > 0 ? "warn" : "neutral"}
        />
      </div>
    </div>
  );
}

export function CommitmentsPage() {
  const entityId = useEntityFilter((s) => s.entityId);
  const [tab, setTab] = useState<Tab>("in");
  const [phantomsOnly, setPhantomsOnly] = useState(false);

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Commitment | undefined>(undefined);
  const [matchingId, setMatchingId] = useState<number | null>(null);

  const directionFilter: CommitmentDirection | undefined =
    tab === "all" ? undefined : tab;

  const kpisQuery = useCommitmentKpis({
    entityId,
    direction: directionFilter,
  });

  const filters = useMemo(
    () => ({
      entityId,
      status: "pending" as CommitmentStatus,
      direction: directionFilter,
      perPage: 200,
    }),
    [entityId, directionFilter],
  );

  const { data, isLoading } = useCommitments(filters);
  const rawItems = data?.items ?? [];

  const items = useMemo(() => {
    let arr = rawItems.slice();
    if (phantomsOnly) {
      arr = arr.filter(isPhantom);
    }
    arr.sort((a, b) => {
      const oa = isOverdue(a) ? 0 : 1;
      const ob = isOverdue(b) ? 0 : 1;
      if (oa !== ob) return oa - ob;
      return a.expected_date.localeCompare(b.expected_date);
    });
    return arr;
  }, [rawItems, phantomsOnly]);

  const cancelMut = useCancelCommitment();
  const updateMut = useUpdateCommitment();

  function handleCancel(c: Commitment) {
    if (
      confirm(
        `Clôturer l'engagement "${c.description ?? c.reference ?? "#" + c.id}" ?`,
      )
    ) {
      cancelMut.mutate(c.id);
    }
  }

  function handleReactivate(c: Commitment) {
    updateMut.mutate({ id: c.id, status: "pending" });
  }

  function openCreate() {
    setEditing(undefined);
    setFormOpen(true);
  }

  function openEdit(c: Commitment) {
    setEditing(c);
    setFormOpen(true);
  }

  function closeForm() {
    setFormOpen(false);
    setEditing(undefined);
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight text-ink">
            À encaisser / À payer
          </h1>
          <p className="mt-0.5 text-[13px] text-muted-foreground">
            Suis tes factures attendues et tes factures à payer, et apparie-les
            aux transactions bancaires.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <EntitySelector />
          <Button onClick={openCreate}>Nouvel engagement</Button>
        </div>
      </div>

      <div className="rounded-xl border border-line-soft bg-panel-2/50 p-4 text-[13px] leading-relaxed text-ink-2">
        <strong className="text-ink">À encaisser / À payer.</strong> Saisis ici
        les factures que tu attends ou que tu dois payer. Elles alimentent ton
        prévisionnel de trésorerie et tes indicateurs BFR/DSO/DPO. Quand une
        transaction réelle correspond à un engagement, il est automatiquement
        marqué comme payé. Vérifie régulièrement les retards pour repérer les
        relances à faire ou les fantômes à clôturer.
      </div>

      <div
        role="tablist"
        aria-label="Direction"
        className="inline-flex rounded-md border border-line-soft bg-panel p-0.5 shadow-card"
      >
        {TABS.map((t) => (
          <button
            key={t.value}
            type="button"
            role="tab"
            aria-selected={tab === t.value}
            onClick={() => {
              setTab(t.value);
              setPhantomsOnly(false);
            }}
            className={
              "rounded px-3 py-1.5 text-[12.5px] font-medium transition-colors " +
              (tab === t.value
                ? "bg-ink text-panel"
                : "text-ink-2 hover:text-ink")
            }
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "all" ? (
        <div className="space-y-4">
          <DirectionKpiTriad
            title="À encaisser"
            kpis={kpisQuery.data?.in}
          />
          <DirectionKpiTriad title="À payer" kpis={kpisQuery.data?.out} />
        </div>
      ) : (
        <DirectionKpiTriad
          title={tab === "in" ? "À encaisser" : "À payer"}
          kpis={tab === "in" ? kpisQuery.data?.in : kpisQuery.data?.out}
        />
      )}

      <GhostCommitmentsBanner
        entityId={entityId}
        direction={directionFilter}
        onShowPhantomsOnly={() => setPhantomsOnly(true)}
      />

      {phantomsOnly && (
        <div className="flex items-center justify-between rounded-md border border-amber-200 bg-amber-50/60 px-3 py-2 text-[12.5px] text-amber-900">
          <span>
            Filtre actif : engagements fantômes (en retard de plus de 7 jours
            sans transaction associée).
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setPhantomsOnly(false)}
          >
            Voir tout
          </Button>
        </div>
      )}

      <div className="overflow-hidden rounded-xl border border-line-soft bg-panel shadow-card">
        {isLoading ? (
          <div className="p-8 text-center text-[13px] text-muted-foreground">
            Chargement…
          </div>
        ) : items.length === 0 ? (
          <div className="p-10 text-center text-[13px] text-muted-foreground">
            {phantomsOnly
              ? "Aucun engagement fantôme."
              : "Aucune échéance enregistrée. Crée une échéance pour qu'elle apparaisse dans ton prévisionnel."}
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-line-soft bg-panel-2">
                <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Statut
                </th>
                <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Tiers
                </th>
                <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Catégorie
                </th>
                <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Date prévue
                </th>
                <th className="px-3 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Montant
                </th>
                {tab === "all" && (
                  <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Sens
                  </th>
                )}
                <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Référence
                </th>
                <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Tx matchée
                </th>
                <th className="px-3 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((c) => {
                const overdue = isOverdue(c);
                return (
                  <tr
                    key={c.id}
                    className="border-b border-line-soft last:border-0 hover:bg-panel-2/40"
                  >
                    <td className="px-3 py-3">
                      <div className="flex flex-wrap items-center gap-1">
                        <StatusBadge status={c.status} />
                        {overdue && <OverdueBadge />}
                      </div>
                    </td>
                    <td className="px-3 py-3 text-[13px] text-ink">
                      <div className="flex flex-col">
                        <span className="truncate">
                          {c.counterparty_name ?? "—"}
                        </span>
                        {c.description && (
                          <span className="truncate text-[11.5px] text-muted-foreground">
                            {c.description}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-3 py-3 text-[12.5px] text-ink-2">
                      {c.category_name ?? "—"}
                    </td>
                    <td
                      className={cn(
                        "px-3 py-3 font-mono text-[12.5px] tabular-nums",
                        overdue ? "text-red-700" : "text-ink",
                      )}
                    >
                      {formatDate(c.expected_date)}
                    </td>
                    <td
                      className={
                        "px-3 py-3 text-right font-mono text-[13px] tabular-nums " +
                        (c.direction === "out" ? "text-debit" : "text-credit")
                      }
                    >
                      {formatCents(c.amount_cents, c.direction)}
                    </td>
                    {tab === "all" && (
                      <td className="px-3 py-3">
                        <DirectionPill direction={c.direction} />
                      </td>
                    )}
                    <td className="px-3 py-3 text-[12.5px] text-ink-2">
                      {c.reference ?? "—"}
                    </td>
                    <td className="px-3 py-3 text-[12.5px] text-ink-2">
                      {c.matched_transaction_id ? (
                        <span className="rounded-md border border-line-soft bg-panel-2 px-2 py-0.5 text-[11.5px] text-muted-foreground">
                          Tx #{c.matched_transaction_id}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="px-3 py-3 text-right">
                      <div className="flex justify-end gap-1">
                        {c.status === "pending" && (
                          <>
                            <button
                              type="button"
                              onClick={() => setMatchingId(c.id)}
                              title="Lie cet engagement à la transaction réelle correspondante. L'engagement passe en 'Payé' et sort du prévisionnel."
                              className="rounded-md border border-line px-2 py-1 text-[11.5px] text-ink-2 hover:border-ink-2 hover:text-ink"
                            >
                              Matcher
                            </button>
                            <button
                              type="button"
                              onClick={() => openEdit(c)}
                              className="rounded-md border border-line px-2 py-1 text-[11.5px] text-ink-2 hover:border-ink-2 hover:text-ink"
                            >
                              Modifier
                            </button>
                            <button
                              type="button"
                              onClick={() => handleCancel(c)}
                              title="Marque l'engagement comme annulé. Il sort du prévisionnel et des indicateurs DSO/DPO. Utilise pour les fantômes ou les factures finalement non émises."
                              className="rounded-md border border-red-200 px-2 py-1 text-[11.5px] text-red-700 hover:bg-red-50"
                            >
                              Clôturer
                            </button>
                          </>
                        )}
                        {c.status === "cancelled" && (
                          <button
                            type="button"
                            onClick={() => handleReactivate(c)}
                            className="rounded-md border border-line px-2 py-1 text-[11.5px] text-ink-2 hover:border-ink-2 hover:text-ink"
                          >
                            Réactiver
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      <CommitmentFormDialog
        open={formOpen}
        onClose={closeForm}
        commitment={editing}
      />
      <CommitmentMatchDialog
        commitmentId={matchingId}
        onClose={() => setMatchingId(null)}
      />
    </section>
  );
}
