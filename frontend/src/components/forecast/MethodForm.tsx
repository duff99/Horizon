import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/api/client";
import { useCategories } from "@/api/categories";
import { useUpsertLine, useValidateFormula } from "@/api/forecastLines";
import type { ForecastLine, ForecastMethod } from "@/types/forecast";
import { cn } from "@/lib/utils";

interface Props {
  scenarioId: number;
  categoryId: number;
  line?: ForecastLine | null;
  onSave: () => void;
}

interface MethodOption {
  value: ForecastMethod;
  title: string;
  description: string;
}

const METHODS: MethodOption[] = [
  {
    value: "RECURRING_FIXED",
    title: "Récurrent à montant fixe",
    description: "Un montant fixe qui se répète chaque mois.",
  },
  {
    value: "AVG_3M",
    title: "Moyenne 3 mois",
    description: "Moyenne des 3 mois précédents (réalisé).",
  },
  {
    value: "AVG_6M",
    title: "Moyenne 6 mois",
    description: "Moyenne des 6 mois précédents (réalisé).",
  },
  {
    value: "AVG_12M",
    title: "Moyenne 12 mois",
    description: "Moyenne des 12 mois précédents (réalisé).",
  },
  {
    value: "PREVIOUS_MONTH",
    title: "Mois précédent",
    description: "Reprend la valeur du mois précédent.",
  },
  {
    value: "SAME_MONTH_LAST_YEAR",
    title: "Même mois l'année précédente",
    description: "Reprend la valeur de N-12.",
  },
  {
    value: "BASED_ON_CATEGORY",
    title: "Basé sur une autre catégorie",
    description: "Un pourcentage d'une autre catégorie (ex : TVA sur ventes).",
  },
  {
    value: "FORMULA",
    title: "Formule personnalisée",
    description:
      "Expression combinant catégories, constantes et opérateurs (ex : cat(101) * 0.2).",
  },
];

export function MethodForm({ scenarioId, categoryId, line, onSave }: Props) {
  const [method, setMethod] = useState<ForecastMethod>(
    line?.method ?? "RECURRING_FIXED",
  );
  const [amountStr, setAmountStr] = useState<string>(() => {
    if (line?.method === "RECURRING_FIXED" && line?.amount_cents != null) {
      return String(line.amount_cents / 100);
    }
    return "";
  });
  const [baseCategoryId, setBaseCategoryId] = useState<number | null>(
    line?.base_category_id ?? null,
  );
  const [ratioStr, setRatioStr] = useState<string>(() => {
    if (line?.ratio != null) {
      return String(Number(line.ratio) * 100);
    }
    return "";
  });
  const [formulaExpr, setFormulaExpr] = useState<string>(
    line?.formula_expr ?? "",
  );
  const [formulaStatus, setFormulaStatus] = useState<
    | { kind: "idle" }
    | { kind: "ok" }
    | { kind: "error"; message: string }
  >({ kind: "idle" });
  const [submitError, setSubmitError] = useState<string | null>(null);

  const categoriesQuery = useCategories();
  const categories = useMemo(() => categoriesQuery.data ?? [], [
    categoriesQuery.data,
  ]);
  const upsertMut = useUpsertLine();
  const validateMut = useValidateFormula();

  // Reset method-local state when switching methods
  useEffect(() => {
    setFormulaStatus({ kind: "idle" });
    setSubmitError(null);
  }, [method]);

  async function handleValidate() {
    if (!formulaExpr.trim()) return;
    try {
      const res = await validateMut.mutateAsync({
        scenario_id: scenarioId,
        formula_expr: formulaExpr.trim(),
        category_id: categoryId,
      });
      if (res.valid) setFormulaStatus({ kind: "ok" });
      else
        setFormulaStatus({
          kind: "error",
          message: res.error ?? "Formule invalide",
        });
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Erreur de validation";
      setFormulaStatus({ kind: "error", message: msg });
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitError(null);
    const payload: Record<string, unknown> = {
      scenario_id: scenarioId,
      category_id: categoryId,
      method,
    };
    try {
      if (method === "RECURRING_FIXED") {
        const parsed = parseFloat(amountStr.replace(",", "."));
        if (!Number.isFinite(parsed)) {
          setSubmitError("Montant invalide");
          return;
        }
        payload.amount_cents = Math.round(parsed * 100);
      } else if (method === "BASED_ON_CATEGORY") {
        if (baseCategoryId == null) {
          setSubmitError("Choisissez une catégorie de référence");
          return;
        }
        const pct = parseFloat(ratioStr.replace(",", "."));
        if (!Number.isFinite(pct) || pct <= 0) {
          setSubmitError("Pourcentage invalide (> 0)");
          return;
        }
        payload.base_category_id = baseCategoryId;
        // Backend expects 0 < ratio <= 10, ratio = pct / 100
        payload.ratio = (pct / 100).toFixed(4);
      } else if (method === "FORMULA") {
        if (!formulaExpr.trim()) {
          setSubmitError("Formule requise");
          return;
        }
        payload.formula_expr = formulaExpr.trim();
      }
      await upsertMut.mutateAsync(
        payload as Parameters<typeof upsertMut.mutateAsync>[0],
      );
      onSave();
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.detail
          : err instanceof Error
            ? err.message
            : "Erreur serveur";
      setSubmitError(msg);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <fieldset className="space-y-1">
        <legend className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          Méthode de calcul
        </legend>
        <div className="space-y-1">
          {METHODS.map((m) => (
            <label
              key={m.value}
              className={cn(
                "flex cursor-pointer items-start gap-3 rounded-md border px-3 py-2 transition-colors",
                method === m.value
                  ? "border-accent/60 bg-accent/5"
                  : "border-line-soft bg-panel hover:border-line-soft hover:bg-panel-2/50",
              )}
            >
              <input
                type="radio"
                name="method"
                value={m.value}
                checked={method === m.value}
                onChange={() => setMethod(m.value)}
                className="mt-0.5 h-3.5 w-3.5 accent-accent"
              />
              <span className="min-w-0 flex-1">
                <span className="block text-[12.5px] font-medium text-ink">
                  {m.title}
                </span>
                <span className="block text-[11.5px] text-muted-foreground">
                  {m.description}
                </span>
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      {method === "RECURRING_FIXED" && (
        <div className="space-y-1">
          <label className="block text-[11.5px] text-ink-2">
            Montant (€) — saisissez un négatif pour un décaissement
          </label>
          <input
            type="number"
            step="0.01"
            value={amountStr}
            onChange={(e) => setAmountStr(e.target.value)}
            className="w-full rounded-md border border-line-soft bg-panel px-2.5 py-1.5 text-right font-mono text-[13px] tabular-nums text-ink"
            placeholder="1500.00"
          />
        </div>
      )}

      {method === "BASED_ON_CATEGORY" && (
        <div className="space-y-3">
          <div className="space-y-1">
            <label className="block text-[11.5px] text-ink-2">
              Catégorie de référence
            </label>
            <select
              value={baseCategoryId ?? ""}
              onChange={(e) =>
                setBaseCategoryId(
                  e.target.value === "" ? null : Number(e.target.value),
                )
              }
              className="w-full rounded-md border border-line-soft bg-panel px-2.5 py-1.5 text-[13px] text-ink"
            >
              <option value="">— choisir —</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <label className="block text-[11.5px] text-ink-2">
              Pourcentage (%)
            </label>
            <input
              type="number"
              step="0.01"
              value={ratioStr}
              onChange={(e) => setRatioStr(e.target.value)}
              className="w-full rounded-md border border-line-soft bg-panel px-2.5 py-1.5 text-right font-mono text-[13px] tabular-nums text-ink"
              placeholder="20 pour 20%"
            />
          </div>
        </div>
      )}

      {method === "FORMULA" && (
        <div className="space-y-2">
          <label className="block text-[11.5px] text-ink-2">
            Expression (ex : cat(101) * 0.2 - cat(200))
          </label>
          <textarea
            value={formulaExpr}
            onChange={(e) => {
              setFormulaExpr(e.target.value);
              setFormulaStatus({ kind: "idle" });
            }}
            rows={3}
            className="w-full rounded-md border border-line-soft bg-panel px-2.5 py-1.5 font-mono text-[12.5px] text-ink"
          />
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleValidate}
              disabled={!formulaExpr.trim() || validateMut.isPending}
              className="h-8"
            >
              Valider la formule
            </Button>
            {formulaStatus.kind === "ok" && (
              <span className="text-[11.5px] text-emerald-700">
                Formule valide.
              </span>
            )}
            {formulaStatus.kind === "error" && (
              <span className="text-[11.5px] text-rose-700">
                {formulaStatus.message}
              </span>
            )}
          </div>
        </div>
      )}

      {submitError && (
        <div
          role="alert"
          className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-[12px] text-rose-700"
        >
          {submitError}
        </div>
      )}

      <div className="flex items-center justify-end gap-2">
        <Button
          type="submit"
          disabled={upsertMut.isPending}
          className="h-9"
        >
          {upsertMut.isPending ? "Enregistrement…" : "Enregistrer"}
        </Button>
      </div>
    </form>
  );
}
