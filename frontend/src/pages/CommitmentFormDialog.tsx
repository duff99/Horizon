import { useEffect, useState } from "react";

import { ApiError } from "@/api/client";
import { useCategories } from "@/api/categories";
import { useCounterparties } from "@/api/counterparties";
import { useEntities } from "@/api/entities";
import {
  useCreateCommitment,
  useUpdateCommitment,
  type Commitment,
  type CommitmentDirection,
} from "@/api/commitments";
import { CategoryCombobox } from "@/components/CategoryCombobox";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useEntityFilter } from "@/stores/entityFilter";

type Props = {
  open: boolean;
  onClose: () => void;
  commitment?: Commitment;
};

type FormState = {
  entity_id: number | null;
  counterparty_id: number | null;
  category_id: number | null;
  direction: CommitmentDirection;
  amount: string;
  issue_date: string;
  expected_date: string;
  reference: string;
  description: string;
};

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

function initialState(
  commitment: Commitment | undefined,
  defaultEntityId: number | null,
): FormState {
  if (commitment) {
    return {
      entity_id: commitment.entity_id,
      counterparty_id: commitment.counterparty_id,
      category_id: commitment.category_id,
      direction: commitment.direction,
      amount: (commitment.amount_cents / 100).toFixed(2),
      issue_date: commitment.issue_date,
      expected_date: commitment.expected_date,
      reference: commitment.reference ?? "",
      description: commitment.description ?? "",
    };
  }
  return {
    entity_id: defaultEntityId,
    counterparty_id: null,
    category_id: null,
    direction: "out",
    amount: "",
    issue_date: todayISO(),
    expected_date: todayISO(),
    reference: "",
    description: "",
  };
}

export function CommitmentFormDialog({ open, onClose, commitment }: Props) {
  const entityFilter = useEntityFilter((s) => s.entityId);
  const { data: entities = [] } = useEntities();
  const [form, setForm] = useState<FormState>(() =>
    initialState(commitment, entityFilter),
  );
  const [clientError, setClientError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const createMut = useCreateCommitment();
  const updateMut = useUpdateCommitment();

  const { data: counterparties = [] } = useCounterparties({
    entityId: form.entity_id,
  });
  const { data: categories = [] } = useCategories();

  useEffect(() => {
    if (open) {
      setForm(initialState(commitment, entityFilter));
      setClientError(null);
      setServerError(null);
      setSuccess(false);
    }
  }, [open, commitment, entityFilter]);

  useEffect(() => {
    if (success) {
      const t = setTimeout(() => onClose(), 1200);
      return () => clearTimeout(t);
    }
  }, [success, onClose]);

  if (!open) return null;

  const isEdit = commitment != null;
  const isPending = createMut.isPending || updateMut.isPending;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setClientError(null);
    setServerError(null);

    if (form.entity_id == null) {
      setClientError("Sélectionnez une société");
      return;
    }
    const amountNum = Number(form.amount.replace(",", "."));
    if (!Number.isFinite(amountNum) || amountNum <= 0) {
      setClientError("Le montant doit être positif");
      return;
    }
    if (form.issue_date > form.expected_date) {
      setClientError(
        "La date d'émission doit être antérieure ou égale à la date prévue",
      );
      return;
    }
    const amount_cents = Math.round(amountNum * 100);

    try {
      if (isEdit && commitment) {
        await updateMut.mutateAsync({
          id: commitment.id,
          counterparty_id: form.counterparty_id,
          category_id: form.category_id,
          direction: form.direction,
          amount_cents,
          issue_date: form.issue_date,
          expected_date: form.expected_date,
          reference: form.reference || null,
          description: form.description || null,
        });
      } else {
        await createMut.mutateAsync({
          entity_id: form.entity_id,
          counterparty_id: form.counterparty_id,
          category_id: form.category_id,
          direction: form.direction,
          amount_cents,
          issue_date: form.issue_date,
          expected_date: form.expected_date,
          reference: form.reference || null,
          description: form.description || null,
        });
      }
      setSuccess(true);
    } catch (err) {
      if (err instanceof ApiError) {
        setServerError(err.detail || "Erreur inconnue");
      } else {
        setServerError("Erreur inconnue");
      }
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="commitment-form-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-[520px] rounded-xl border border-line-soft bg-panel p-6 shadow-card">
        <div>
          <h2
            id="commitment-form-title"
            className="text-[16px] font-semibold text-ink"
          >
            {isEdit ? "Modifier l'engagement" : "Nouvel engagement"}
          </h2>
          <p className="mt-0.5 text-[12.5px] text-muted-foreground">
            {isEdit
              ? "Mettez à jour les informations de cet engagement."
              : "Enregistrez une facture ou un paiement à venir."}
          </p>
        </div>

        {success ? (
          <div className="mt-6 space-y-4">
            <div
              role="status"
              className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-[12.5px] text-emerald-800"
            >
              {isEdit ? "Engagement mis à jour" : "Engagement créé"}
            </div>
            <div className="flex justify-end">
              <Button type="button" onClick={onClose}>
                Fermer
              </Button>
            </div>
          </div>
        ) : (
          <form className="mt-4 space-y-3" onSubmit={handleSubmit}>
            {!isEdit && (
              <div className="space-y-1.5">
                <Label className="text-[12.5px] font-medium text-ink-2">
                  Société
                </Label>
                <select
                  required
                  value={form.entity_id == null ? "" : String(form.entity_id)}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      entity_id:
                        e.target.value === "" ? null : Number(e.target.value),
                    }))
                  }
                  className="w-full rounded-md border border-line-soft bg-panel px-2.5 py-1.5 text-[13px] text-ink"
                >
                  <option value="">— choisir —</option>
                  {entities.map((ent) => (
                    <option key={ent.id} value={ent.id}>
                      {ent.name}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div className="space-y-1.5">
              <Label className="text-[12.5px] font-medium text-ink-2">
                Direction
              </Label>
              <div
                role="radiogroup"
                aria-label="Direction"
                className="inline-flex rounded-md border border-line-soft bg-panel-2 p-0.5"
              >
                {(["out", "in"] as CommitmentDirection[]).map((d) => (
                  <button
                    key={d}
                    type="button"
                    role="radio"
                    aria-checked={form.direction === d}
                    onClick={() =>
                      setForm((f) => ({ ...f, direction: d }))
                    }
                    className={
                      "rounded px-3 py-1.5 text-[12.5px] font-medium transition-colors " +
                      (form.direction === d
                        ? "bg-ink text-panel"
                        : "text-ink-2 hover:text-ink")
                    }
                  >
                    {d === "in" ? "Entrée" : "Sortie"}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label
                  htmlFor="commitment-amount"
                  className="text-[12.5px] font-medium text-ink-2"
                >
                  Montant (€)
                </Label>
                <Input
                  id="commitment-amount"
                  type="number"
                  step="0.01"
                  min="0"
                  required
                  value={form.amount}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, amount: e.target.value }))
                  }
                  className="text-right font-mono tabular-nums"
                  placeholder="0.00"
                />
              </div>
              <div className="space-y-1.5">
                <Label
                  htmlFor="commitment-reference"
                  className="text-[12.5px] font-medium text-ink-2"
                >
                  Référence
                </Label>
                <Input
                  id="commitment-reference"
                  type="text"
                  value={form.reference}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, reference: e.target.value }))
                  }
                  placeholder="FAC-2026-001"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label
                  htmlFor="commitment-issue-date"
                  className="text-[12.5px] font-medium text-ink-2"
                >
                  Date d'émission
                </Label>
                <Input
                  id="commitment-issue-date"
                  type="date"
                  required
                  value={form.issue_date}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, issue_date: e.target.value }))
                  }
                />
              </div>
              <div className="space-y-1.5">
                <Label
                  htmlFor="commitment-expected-date"
                  className="text-[12.5px] font-medium text-ink-2"
                >
                  Date prévue
                </Label>
                <Input
                  id="commitment-expected-date"
                  type="date"
                  required
                  value={form.expected_date}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, expected_date: e.target.value }))
                  }
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label className="text-[12.5px] font-medium text-ink-2">
                Tiers
              </Label>
              <select
                value={
                  form.counterparty_id == null
                    ? ""
                    : String(form.counterparty_id)
                }
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    counterparty_id:
                      e.target.value === "" ? null : Number(e.target.value),
                  }))
                }
                className="w-full rounded-md border border-line-soft bg-panel px-2.5 py-1.5 text-[13px] text-ink"
              >
                <option value="">— aucun —</option>
                {counterparties.map((cp) => (
                  <option key={cp.id} value={cp.id}>
                    {cp.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <Label className="text-[12.5px] font-medium text-ink-2">
                Catégorie
              </Label>
              <CategoryCombobox
                categories={categories}
                value={form.category_id}
                onChange={(id) =>
                  setForm((f) => ({ ...f, category_id: id }))
                }
                placeholder="— aucune —"
              />
            </div>

            <div className="space-y-1.5">
              <Label
                htmlFor="commitment-description"
                className="text-[12.5px] font-medium text-ink-2"
              >
                Description
              </Label>
              <textarea
                id="commitment-description"
                rows={2}
                value={form.description}
                onChange={(e) =>
                  setForm((f) => ({ ...f, description: e.target.value }))
                }
                className="w-full rounded-md border border-line-soft bg-panel px-2.5 py-1.5 text-[13px] text-ink"
                placeholder="Notes internes…"
              />
            </div>

            {clientError && (
              <div
                role="alert"
                className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-[12.5px] text-red-800"
              >
                {clientError}
              </div>
            )}
            {serverError && (
              <div
                role="alert"
                className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-[12.5px] text-red-800"
              >
                {serverError}
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="ghost" onClick={onClose}>
                Annuler
              </Button>
              <Button type="submit" disabled={isPending}>
                {isPending
                  ? "Enregistrement…"
                  : isEdit
                    ? "Enregistrer"
                    : "Créer"}
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
