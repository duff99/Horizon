import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Button } from "@/components/ui/button";
import { useEntities } from "../api/entities";
import { useEntityFilter } from "../stores/entityFilter";
import { EntitySelector } from "@/components/EntitySelector";
import {
  createForecastEntry,
  deleteForecastEntry,
  fetchForecastProjection,
  fetchRecurringSuggestions,
  listForecastEntries,
  updateForecastEntry,
  type DetectedRecurrenceSuggestion,
  type ForecastEntry,
  type ForecastRecurrence,
} from "../api/forecast";

const EUR = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 2,
});

const DATE_SHORT = new Intl.DateTimeFormat("fr-FR", {
  day: "2-digit",
  month: "short",
});

function formatEUR(v: string | number): string {
  const n = typeof v === "string" ? Number(v) : v;
  return Number.isFinite(n) ? EUR.format(n) : "—";
}

const RECURRENCE_LABELS: Record<ForecastRecurrence, string> = {
  NONE: "Ponctuel",
  WEEKLY: "Hebdomadaire",
  MONTHLY: "Mensuel",
  QUARTERLY: "Trimestriel",
  YEARLY: "Annuel",
};

const HORIZONS = [
  { value: 30, label: "30 j" },
  { value: 60, label: "60 j" },
  { value: 90, label: "90 j" },
];

type FormState = {
  id: number | null;
  entity_id: number | "";
  label: string;
  amount: string;
  due_date: string;
  recurrence: ForecastRecurrence;
  notes: string;
};

const emptyForm: FormState = {
  id: null,
  entity_id: "",
  label: "",
  amount: "",
  due_date: new Date().toISOString().slice(0, 10),
  recurrence: "NONE",
  notes: "",
};

export function ForecastPage() {
  const qc = useQueryClient();
  const { data: entities = [] } = useEntities();
  const entityId = useEntityFilter((s) => s.entityId);
  const [horizon, setHorizon] = useState<number>(90);
  const [form, setForm] = useState<FormState>(emptyForm);

  const entityIdForQueries = entityId ?? undefined;

  const { data: projection, isLoading: projLoading } = useQuery({
    queryKey: ["forecast-projection", horizon, entityIdForQueries],
    queryFn: () =>
      fetchForecastProjection({ horizonDays: horizon, entityId: entityIdForQueries }),
    staleTime: 60_000,
  });

  const { data: entries = [], isLoading: entriesLoading } = useQuery({
    queryKey: ["forecast-entries", entityIdForQueries],
    queryFn: () => listForecastEntries(entityIdForQueries),
  });

  const suggestionsEntityId =
    entityId != null
      ? entityId
      : entities.length === 1
        ? entities[0].id
        : undefined;

  const { data: suggestions = [] } = useQuery({
    queryKey: ["forecast-suggestions", suggestionsEntityId],
    queryFn: () => fetchRecurringSuggestions(suggestionsEntityId!),
    enabled: suggestionsEntityId !== undefined,
    staleTime: 5 * 60_000,
  });

  const createMut = useMutation({
    mutationFn: (payload: Parameters<typeof createForecastEntry>[0]) =>
      createForecastEntry(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["forecast-entries"] });
      qc.invalidateQueries({ queryKey: ["forecast-projection"] });
      setForm(emptyForm);
    },
  });
  const updateMut = useMutation({
    mutationFn: (args: { id: number; payload: Parameters<typeof updateForecastEntry>[1] }) =>
      updateForecastEntry(args.id, args.payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["forecast-entries"] });
      qc.invalidateQueries({ queryKey: ["forecast-projection"] });
      setForm(emptyForm);
    },
  });
  const deleteMut = useMutation({
    mutationFn: (id: number) => deleteForecastEntry(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["forecast-entries"] });
      qc.invalidateQueries({ queryKey: ["forecast-projection"] });
    },
  });

  const chartData = useMemo(() => {
    if (!projection) return [];
    return projection.points.map((p) => ({
      date: p.date,
      dateLabel: DATE_SHORT.format(new Date(p.date)),
      Solde: Number(p.balance),
    }));
  }, [projection]);

  const terminalBalance = useMemo(() => {
    if (!projection || projection.points.length === 0) return null;
    return projection.points[projection.points.length - 1].balance;
  }, [projection]);

  function startEdit(e: ForecastEntry) {
    setForm({
      id: e.id,
      entity_id: e.entity_id,
      label: e.label,
      amount: e.amount,
      due_date: e.due_date,
      recurrence: e.recurrence,
      notes: e.notes ?? "",
    });
  }

  function handleSubmit(ev: React.FormEvent) {
    ev.preventDefault();
    if (form.entity_id === "" || !form.label.trim()) return;
    if (form.id == null) {
      createMut.mutate({
        entity_id: form.entity_id,
        label: form.label.trim(),
        amount: form.amount,
        due_date: form.due_date,
        recurrence: form.recurrence,
        notes: form.notes || null,
      });
    } else {
      updateMut.mutate({
        id: form.id,
        payload: {
          label: form.label.trim(),
          amount: form.amount,
          due_date: form.due_date,
          recurrence: form.recurrence,
          notes: form.notes || null,
        },
      });
    }
  }

  function materializeSuggestion(s: DetectedRecurrenceSuggestion) {
    createMut.mutate({
      entity_id: s.entity_id,
      label: s.counterparty_name,
      amount: s.average_amount,
      due_date: s.next_expected,
      recurrence: s.recurrence,
      counterparty_id: s.counterparty_id ?? null,
      notes: "Généré depuis la détection automatique",
    });
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight text-ink">
            Prévisionnel de trésorerie
          </h1>
          <p className="mt-0.5 text-[13px] text-muted-foreground">
            Projetez votre solde à 30/60/90 jours en combinant entrées
            manuelles et récurrences détectées.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <EntitySelector />
          <div
            role="tablist"
            aria-label="Horizon"
            className="inline-flex rounded-md border border-line-soft bg-panel p-0.5 shadow-card"
          >
            {HORIZONS.map((h) => (
              <button
                key={h.value}
                type="button"
                role="tab"
                aria-selected={horizon === h.value}
                onClick={() => setHorizon(h.value)}
                className={
                  "px-3 py-1.5 text-[12.5px] font-medium transition-colors rounded " +
                  (horizon === h.value
                    ? "bg-ink text-panel"
                    : "text-ink-2 hover:text-ink")
                }
              >
                {h.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-line-soft bg-panel p-5 shadow-card">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Solde de départ
          </div>
          <div className="mt-2 font-mono text-[20px] font-semibold tabular-nums text-ink">
            {projection ? formatEUR(projection.starting_balance) : "—"}
          </div>
          <div className="mt-1 text-[12px] text-muted-foreground">
            {projection
              ? `au ${new Date(projection.starting_date).toLocaleDateString("fr-FR")}`
              : " "}
          </div>
        </div>
        <div className="rounded-xl border border-line-soft bg-panel p-5 shadow-card">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Solde projeté J+{horizon}
          </div>
          <div
            className={
              "mt-2 font-mono text-[20px] font-semibold tabular-nums " +
              (terminalBalance != null && Number(terminalBalance) < 0
                ? "text-debit"
                : "text-ink")
            }
          >
            {terminalBalance != null ? formatEUR(terminalBalance) : "—"}
          </div>
          <div className="mt-1 text-[12px] text-muted-foreground">
            Basé sur les entrées prévisionnelles actuelles
          </div>
        </div>
        <div className="rounded-xl border border-line-soft bg-panel p-5 shadow-card">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Entrées planifiées
          </div>
          <div className="mt-2 font-mono text-[20px] font-semibold tabular-nums text-ink">
            {entries.length}
          </div>
          <div className="mt-1 text-[12px] text-muted-foreground">
            dont {entries.filter((e) => e.recurrence !== "NONE").length} récurrentes
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-line-soft bg-panel p-4 shadow-card">
        <div className="mb-3 text-[13px] font-semibold text-ink">
          Projection du solde
        </div>
        {projLoading || !projection ? (
          <div className="flex h-[280px] items-center justify-center text-[13px] text-muted-foreground">
            Chargement…
          </div>
        ) : (
          <div style={{ width: "100%", height: 280 }}>
            <ResponsiveContainer>
              <AreaChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
                <defs>
                  <linearGradient id="proj-grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="hsl(var(--accent))" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="hsl(var(--accent))" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="2 2" stroke="hsl(var(--line))" vertical={false} />
                <XAxis
                  dataKey="dateLabel"
                  tick={{ fontSize: 11, fill: "hsl(var(--muted-fg))" }}
                  axisLine={{ stroke: "hsl(var(--line))" }}
                  tickLine={false}
                  minTickGap={24}
                />
                <YAxis
                  tick={{ fontSize: 11, fill: "hsl(var(--muted-fg))" }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v) => EUR.format(Number(v)).replace(/\u202f?€/, "")}
                  width={72}
                />
                <Tooltip
                  contentStyle={{
                    background: "hsl(var(--panel))",
                    border: "1px solid hsl(var(--line))",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                  formatter={(v) => formatEUR(Number(v))}
                />
                <ReferenceLine y={0} stroke="hsl(var(--debit))" strokeDasharray="3 3" />
                <Area
                  type="monotone"
                  dataKey="Solde"
                  stroke="hsl(var(--accent))"
                  strokeWidth={2}
                  fill="url(#proj-grad)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-line-soft bg-panel p-4 shadow-card">
          <div className="mb-3 text-[13px] font-semibold text-ink">
            {form.id == null ? "Ajouter une entrée" : "Modifier l'entrée"}
          </div>
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <label className="col-span-2 text-[12px] text-ink-2">
                Société
                <select
                  required
                  value={form.entity_id === "" ? "" : String(form.entity_id)}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      entity_id: e.target.value === "" ? "" : Number(e.target.value),
                    }))
                  }
                  disabled={form.id !== null}
                  className="mt-1 w-full rounded-md border border-line-soft bg-panel px-2.5 py-1.5 text-[13px] text-ink disabled:opacity-60"
                >
                  <option value="">— choisir —</option>
                  {entities.map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="col-span-2 text-[12px] text-ink-2">
                Libellé
                <input
                  required
                  type="text"
                  value={form.label}
                  onChange={(e) => setForm((f) => ({ ...f, label: e.target.value }))}
                  className="mt-1 w-full rounded-md border border-line-soft bg-panel px-2.5 py-1.5 text-[13px] text-ink"
                  placeholder="Loyer bureaux, TVA, salaire..."
                />
              </label>
              <label className="text-[12px] text-ink-2">
                Montant (signé)
                <input
                  required
                  type="number"
                  step="0.01"
                  value={form.amount}
                  onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
                  className="mt-1 w-full rounded-md border border-line-soft bg-panel px-2.5 py-1.5 text-right font-mono text-[13px] tabular-nums text-ink"
                  placeholder="-1500.00"
                />
              </label>
              <label className="text-[12px] text-ink-2">
                Date d'effet
                <input
                  required
                  type="date"
                  value={form.due_date}
                  onChange={(e) => setForm((f) => ({ ...f, due_date: e.target.value }))}
                  className="mt-1 w-full rounded-md border border-line-soft bg-panel px-2.5 py-1.5 text-[13px] text-ink"
                />
              </label>
              <label className="col-span-2 text-[12px] text-ink-2">
                Récurrence
                <select
                  value={form.recurrence}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      recurrence: e.target.value as ForecastRecurrence,
                    }))
                  }
                  className="mt-1 w-full rounded-md border border-line-soft bg-panel px-2.5 py-1.5 text-[13px] text-ink"
                >
                  {(Object.keys(RECURRENCE_LABELS) as ForecastRecurrence[]).map((k) => (
                    <option key={k} value={k}>
                      {RECURRENCE_LABELS[k]}
                    </option>
                  ))}
                </select>
              </label>
              <label className="col-span-2 text-[12px] text-ink-2">
                Notes
                <textarea
                  value={form.notes}
                  onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                  rows={2}
                  className="mt-1 w-full rounded-md border border-line-soft bg-panel px-2.5 py-1.5 text-[13px] text-ink"
                />
              </label>
            </div>
            <div className="flex items-center gap-2">
              <Button type="submit" disabled={createMut.isPending || updateMut.isPending}>
                {form.id == null ? "Ajouter" : "Enregistrer"}
              </Button>
              {form.id != null && (
                <Button type="button" variant="outline" onClick={() => setForm(emptyForm)}>
                  Annuler
                </Button>
              )}
            </div>
            {(createMut.error || updateMut.error) && (
              <div role="alert" className="text-[12.5px] text-debit">
                {(createMut.error ?? updateMut.error)!.message}
              </div>
            )}
          </form>
        </div>

        <div className="rounded-xl border border-line-soft bg-panel p-4 shadow-card">
          <div className="mb-3 flex items-baseline justify-between">
            <div className="text-[13px] font-semibold text-ink">
              Récurrences détectées
            </div>
            <div className="text-[11px] text-muted-foreground">
              {suggestionsEntityId == null
                ? "Sélectionnez une entité"
                : `${suggestions.length} proposition(s)`}
            </div>
          </div>
          {suggestions.length === 0 ? (
            <div className="text-[13px] text-muted-foreground">
              Aucune récurrence détectée pour l'instant.
            </div>
          ) : (
            <ul className="space-y-2">
              {suggestions.slice(0, 8).map((s) => (
                <li
                  key={`${s.counterparty_id}-${s.recurrence}`}
                  className="flex items-center justify-between gap-3 rounded-md border border-line-soft bg-panel-2 px-3 py-2"
                >
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-[13px] font-medium text-ink">
                      {s.counterparty_name}
                    </div>
                    <div className="text-[11.5px] text-muted-foreground">
                      {RECURRENCE_LABELS[s.recurrence]} — prochaine attendue le{" "}
                      {new Date(s.next_expected).toLocaleDateString("fr-FR")} —{" "}
                      {s.occurrences_count} occurrences
                    </div>
                  </div>
                  <div
                    className={
                      "font-mono text-[13px] tabular-nums " +
                      (Number(s.average_amount) < 0 ? "text-debit" : "text-credit")
                    }
                  >
                    {formatEUR(s.average_amount)}
                  </div>
                  <button
                    type="button"
                    onClick={() => materializeSuggestion(s)}
                    className="rounded-md border border-line px-2 py-1 text-[11.5px] text-ink-2 hover:border-ink-2"
                  >
                    Ajouter
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-line-soft bg-panel shadow-card">
        <div className="border-b border-line-soft px-4 py-3 text-[13px] font-semibold text-ink">
          Entrées prévisionnelles
        </div>
        {entriesLoading ? (
          <div className="p-6 text-center text-[13px] text-muted-foreground">Chargement…</div>
        ) : entries.length === 0 ? (
          <div className="p-6 text-center text-[13px] text-muted-foreground">
            Aucune entrée prévisionnelle. Ajoutez-en via le formulaire ci-dessus.
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-line-soft bg-panel-2">
                <th className="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Date
                </th>
                <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Libellé
                </th>
                <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Récurrence
                </th>
                <th className="px-3 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Montant
                </th>
                <th className="px-3 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.id} className="border-b border-line-soft last:border-0">
                  <td className="px-4 py-3 font-mono text-[12.5px] tabular-nums text-ink-2">
                    {new Date(e.due_date).toLocaleDateString("fr-FR")}
                  </td>
                  <td className="px-3 py-3 text-[13px] text-ink">
                    <div className="flex flex-col">
                      <span>{e.label}</span>
                      {e.notes && (
                        <span className="text-[11.5px] text-muted-foreground">
                          {e.notes}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-3 py-3 text-[12.5px] text-ink-2">
                    {RECURRENCE_LABELS[e.recurrence]}
                  </td>
                  <td
                    className={
                      "px-3 py-3 text-right font-mono text-[13px] tabular-nums " +
                      (Number(e.amount) < 0 ? "text-debit" : "text-credit")
                    }
                  >
                    {formatEUR(e.amount)}
                  </td>
                  <td className="px-3 py-3 text-right">
                    <button
                      type="button"
                      onClick={() => startEdit(e)}
                      className="mr-2 rounded-md border border-line px-2 py-1 text-[11.5px] text-ink-2 hover:border-ink-2"
                    >
                      Modifier
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        if (confirm(`Supprimer "${e.label}" ?`)) deleteMut.mutate(e.id);
                      }}
                      className="rounded-md border border-red-200 px-2 py-1 text-[11.5px] text-red-700 hover:bg-red-50"
                    >
                      Supprimer
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
