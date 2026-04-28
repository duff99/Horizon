import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { DatePicker } from "@/components/ui/date-picker";
import { EntitySelector } from "@/components/EntitySelector";
import { useEntityFilter } from "../stores/entityFilter";
import {
  useCancelCommitment,
  useCommitments,
  useUpdateCommitment,
  type Commitment,
  type CommitmentDirection,
  type CommitmentStatus,
} from "../api/commitments";
import { CommitmentFormDialog } from "./CommitmentFormDialog";
import { CommitmentMatchDialog } from "./CommitmentMatchDialog";

const EUR = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 2,
});

function formatCents(cents: number, direction: CommitmentDirection): string {
  const signed = direction === "out" ? -cents : cents;
  return EUR.format(signed / 100);
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("fr-FR");
}

const STATUS_TABS: { value: CommitmentStatus; label: string }[] = [
  { value: "pending", label: "En attente" },
  { value: "paid", label: "Payés" },
  { value: "cancelled", label: "Annulés" },
];

const DIRECTION_OPTIONS: {
  value: CommitmentDirection | "all";
  label: string;
}[] = [
  { value: "all", label: "Toutes" },
  { value: "in", label: "Entrées" },
  { value: "out", label: "Sorties" },
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

function DirectionPill({ direction }: { direction: CommitmentDirection }) {
  const styles =
    direction === "in"
      ? "border-emerald-200 bg-emerald-50 text-emerald-800"
      : "border-rose-200 bg-rose-50 text-rose-800";
  const label = direction === "in" ? "Entrée" : "Sortie";
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

export function CommitmentsPage() {
  const entityId = useEntityFilter((s) => s.entityId);
  const [status, setStatus] = useState<CommitmentStatus>("pending");
  const [direction, setDirection] = useState<CommitmentDirection | "all">(
    "all",
  );
  const [from, setFrom] = useState<string>("");
  const [to, setTo] = useState<string>("");

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Commitment | undefined>(undefined);
  const [matchingId, setMatchingId] = useState<number | null>(null);

  const filters = useMemo(
    () => ({
      entityId,
      status,
      direction: direction === "all" ? undefined : direction,
      from: from || undefined,
      to: to || undefined,
      perPage: 100,
    }),
    [entityId, status, direction, from, to],
  );

  const { data, isLoading } = useCommitments(filters);
  const items = data?.items ?? [];

  const cancelMut = useCancelCommitment();
  const updateMut = useUpdateCommitment();

  function handleCancel(c: Commitment) {
    if (
      confirm(
        `Annuler l'engagement "${c.description ?? c.reference ?? "#" + c.id}" ?`,
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
            Engagements
          </h1>
          <p className="mt-0.5 text-[13px] text-muted-foreground">
            Suivez vos factures et engagements à venir, puis appariez-les aux
            transactions bancaires.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <EntitySelector />
          <Button onClick={openCreate}>Nouvel engagement</Button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 rounded-md border border-line-soft bg-panel p-2 shadow-card">
        <div
          role="tablist"
          aria-label="Statut"
          className="inline-flex rounded-md border border-line-soft bg-panel-2 p-0.5"
        >
          {STATUS_TABS.map((t) => (
            <button
              key={t.value}
              type="button"
              role="tab"
              aria-selected={status === t.value}
              onClick={() => setStatus(t.value)}
              className={
                "rounded px-3 py-1.5 text-[12.5px] font-medium transition-colors " +
                (status === t.value
                  ? "bg-ink text-panel"
                  : "text-ink-2 hover:text-ink")
              }
            >
              {t.label}
            </button>
          ))}
        </div>

        <div
          role="radiogroup"
          aria-label="Direction"
          className="inline-flex rounded-md border border-line-soft bg-panel-2 p-0.5"
        >
          {DIRECTION_OPTIONS.map((d) => (
            <button
              key={d.value}
              type="button"
              role="radio"
              aria-checked={direction === d.value}
              onClick={() => setDirection(d.value)}
              className={
                "rounded px-3 py-1.5 text-[12.5px] font-medium transition-colors " +
                (direction === d.value
                  ? "bg-ink text-panel"
                  : "text-ink-2 hover:text-ink")
              }
            >
              {d.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1.5 text-[12px] text-ink-2">
          <label className="flex items-center gap-1">
            Du
            <div className="w-[140px]">
              <DatePicker
                value={from}
                onChange={setFrom}
                placeholder="—"
                aria-label="Date de début"
              />
            </div>
          </label>
          <label className="flex items-center gap-1">
            au
            <div className="w-[140px]">
              <DatePicker
                value={to}
                onChange={setTo}
                placeholder="—"
                aria-label="Date de fin"
              />
            </div>
          </label>
          {(from || to) && (
            <button
              type="button"
              onClick={() => {
                setFrom("");
                setTo("");
              }}
              className="rounded-md px-2 py-1 text-[11.5px] text-muted-foreground hover:text-ink"
            >
              Réinitialiser
            </button>
          )}
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-line-soft bg-panel shadow-card">
        {isLoading ? (
          <div className="p-8 text-center text-[13px] text-muted-foreground">
            Chargement…
          </div>
        ) : items.length === 0 ? (
          <div className="p-10 text-center text-[13px] text-muted-foreground">
            Aucun engagement — créez-en un pour suivre vos factures à venir.
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-line-soft bg-panel-2">
                <th className="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Émission
                </th>
                <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Prévue
                </th>
                <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Tiers
                </th>
                <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Catégorie
                </th>
                <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Direction
                </th>
                <th className="px-3 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Montant
                </th>
                <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Statut
                </th>
                <th className="px-3 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((c) => (
                <tr
                  key={c.id}
                  className="border-b border-line-soft last:border-0 hover:bg-panel-2/40"
                >
                  <td className="px-4 py-3 font-mono text-[12.5px] tabular-nums text-ink-2">
                    {formatDate(c.issue_date)}
                  </td>
                  <td className="px-3 py-3 font-mono text-[12.5px] tabular-nums text-ink">
                    {formatDate(c.expected_date)}
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
                  <td className="px-3 py-3">
                    <DirectionPill direction={c.direction} />
                  </td>
                  <td
                    className={
                      "px-3 py-3 text-right font-mono text-[13px] tabular-nums " +
                      (c.direction === "out" ? "text-debit" : "text-credit")
                    }
                  >
                    {formatCents(c.amount_cents, c.direction)}
                  </td>
                  <td className="px-3 py-3">
                    <StatusBadge status={c.status} />
                  </td>
                  <td className="px-3 py-3 text-right">
                    <div className="flex justify-end gap-1">
                      {c.status === "pending" && (
                        <>
                          <button
                            type="button"
                            onClick={() => setMatchingId(c.id)}
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
                            className="rounded-md border border-red-200 px-2 py-1 text-[11.5px] text-red-700 hover:bg-red-50"
                          >
                            Annuler
                          </button>
                        </>
                      )}
                      {c.status === "paid" && c.matched_transaction_id && (
                        <span className="rounded-md border border-line-soft bg-panel-2 px-2 py-1 text-[11.5px] text-muted-foreground">
                          Tx #{c.matched_transaction_id}
                        </span>
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
              ))}
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
