import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { MonthPicker } from "@/components/ui/month-picker";
import { ApiError } from "@/api/client";
import { useCategories } from "@/api/categories";
import {
  useDeleteLine,
  useUpsertLine,
  useValidateFormula,
} from "@/api/forecastLines";
import type {
  ForecastLine,
  ForecastMethod,
  LineUpsert,
} from "@/types/forecast";
import { cn } from "@/lib/utils";

interface Props {
  scenarioId: number;
  categoryId: number;
  /**
   * Direction du flux pour cette ligne (déduite de la section du pivot
   * cliquée : Encaissements → "in", Décaissements → "out"). L'utilisateur
   * saisit toujours un montant positif ; le signe est appliqué
   * automatiquement à l'enregistrement.
   */
  direction: "in" | "out";
  /**
   * Mois (format "YYYY-MM") de la cellule cliquée dans le pivot. Sert de
   * valeur initiale pour la méthode SINGLE_MONTH_FIXED — l'utilisateur
   * vient de cliquer sur ce mois précis, on pré-remplit donc le sélecteur.
   */
  cellMonth?: string;
  line?: ForecastLine | null;
  onSave: () => void;
  /** D6 — pré-remplissage depuis RecurringSuggestionPicker (montant en centimes). */
  prefillAmountCents?: number;
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
    value: "SINGLE_MONTH_FIXED",
    title: "Montant ponctuel — un seul mois",
    description:
      "Un montant fixe appliqué une seule fois sur le mois choisi (ex : encaissement client exceptionnel).",
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

export function MethodForm({
  scenarioId,
  categoryId,
  direction,
  cellMonth,
  line,
  onSave,
  prefillAmountCents,
}: Props) {
  const isOut = direction === "out";
  const [method, setMethod] = useState<ForecastMethod>(
    prefillAmountCents != null
      ? "RECURRING_FIXED"
      : (line?.method ?? "RECURRING_FIXED"),
  );
  // L'input affiche toujours la valeur ABSOLUE ; le signe est rétabli à
  // l'enregistrement selon `direction`. Évite que l'utilisateur ait à
  // se rappeler de mettre un "-" pour un décaissement.
  const [amountStr, setAmountStr] = useState<string>(() => {
    if (prefillAmountCents != null) {
      return String(Math.abs(prefillAmountCents) / 100);
    }
    if (
      (line?.method === "RECURRING_FIXED" || line?.method === "SINGLE_MONTH_FIXED") &&
      line?.amount_cents != null
    ) {
      return String(Math.abs(line.amount_cents) / 100);
    }
    return "";
  });
  // Mois cible pour SINGLE_MONTH_FIXED : initialisé depuis la ligne existante
  // si elle est en single-month, sinon depuis la cellule cliquée. Format "YYYY-MM".
  const [singleMonth, setSingleMonth] = useState<string>(() => {
    if (line?.method === "SINGLE_MONTH_FIXED" && line.start_month) {
      return line.start_month.slice(0, 7);
    }
    return cellMonth ?? "";
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

  // Portée temporelle de la règle. Détermine start_month / end_month à
  // l'enregistrement et permet de coexister avec d'autres règles sur la
  // même catégorie (ex : ponctuelle Mai + récurrente Juin+).
  //   - "from_this_month" → start_month = mois cliqué, end_month = NULL.
  //   - "this_month_only" → start_month = end_month = mois cliqué.
  // SINGLE_MONTH_FIXED force toujours "this_month_only".
  type Scope = "from_this_month" | "this_month_only";
  const [scope, setScope] = useState<Scope>(() => {
    if (line?.method === "SINGLE_MONTH_FIXED") return "this_month_only";
    if (
      line?.start_month != null &&
      line?.end_month != null &&
      line.start_month === line.end_month
    ) {
      return "this_month_only";
    }
    return "from_this_month";
  });
  const [formulaStatus, setFormulaStatus] = useState<
    | { kind: "idle" }
    | { kind: "ok" }
    | { kind: "error"; message: string }
  >({ kind: "idle" });
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);

  const categoriesQuery = useCategories();
  const categories = useMemo(() => categoriesQuery.data ?? [], [
    categoriesQuery.data,
  ]);
  const upsertMut = useUpsertLine();
  const deleteMut = useDeleteLine();
  const validateMut = useValidateFormula();

  // Reset method-local state when switching methods
  useEffect(() => {
    setFormulaStatus({ kind: "idle" });
    setSubmitError(null);
  }, [method]);

  /**
   * Normalise une saisie utilisateur en nombre. Gère :
   *  - virgule décimale française ("10,5" → 10.5)
   *  - séparateurs de milliers (espace fine, espace insécable, espace
   *    standard, point comme séparateur de milliers anglo-saxon n'est PAS
   *    supporté pour éviter les ambiguïtés avec la décimale française).
   *  - symbole € éventuel collé au montant ("10 000 €" → 10000).
   *
   * Plus robuste que `parseFloat(str.replace(",", "."))` qui sautait
   * silencieusement à NaN dès qu'un espace de milliers traînait.
   */
  function parseAmount(raw: string): number {
    const cleaned = raw
      .replace(/ /g, "") // espace insécable
      .replace(/ /g, "") // espace fine insécable
      .replace(/\s+/g, "") // tous les espaces classiques
      .replace(/€/g, "")
      .replace(",", ".");
    return parseFloat(cleaned);
  }

  // Aperçu en clair du montant saisi pour rassurer l'utilisateur. On
  // applique le signe déduit de `direction` pour afficher la valeur telle
  // qu'elle apparaîtra dans le pivot (négative pour un décaissement).
  const parsedAbs =
    amountStr.trim().length > 0 ? Math.abs(parseAmount(amountStr)) : NaN;
  const previewAmount = Number.isFinite(parsedAbs)
    ? (isOut ? -parsedAbs : parsedAbs)
    : NaN;
  const previewLabel = Number.isFinite(previewAmount)
    ? new Intl.NumberFormat("fr-FR", {
        style: "currency",
        currency: "EUR",
      }).format(previewAmount)
    : null;

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

  async function handleDeleteConfirmed() {
    if (!line) return;
    setSubmitError(null);
    try {
      await deleteMut.mutateAsync({
        id: line.id,
        categoryId: line.category_id,
        scenarioId: line.scenario_id,
      });
      setConfirmDeleteOpen(false);
      onSave();
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.detail
          : err instanceof Error
            ? err.message
            : "Erreur serveur";
      setSubmitError(msg);
      setConfirmDeleteOpen(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitError(null);
    const payload: LineUpsert = {
      scenario_id: scenarioId,
      category_id: categoryId,
      method,
    };
    // Portée appliquée à toutes les méthodes sauf SINGLE_MONTH_FIXED qui
    // gère son propre mois via le picker existant.
    if (method !== "SINGLE_MONTH_FIXED" && cellMonth) {
      const monthIso = `${cellMonth}-01`;
      payload.start_month = monthIso;
      payload.end_month = scope === "this_month_only" ? monthIso : null;
    }
    try {
      if (method === "RECURRING_FIXED") {
        const parsed = parseAmount(amountStr);
        if (!Number.isFinite(parsed)) {
          setSubmitError("Montant invalide. Saisissez un nombre, ex : 1500.");
          return;
        }
        // Signe inféré depuis la direction : positif pour Encaissements,
        // négatif pour Décaissements. La valeur absolue saisie est
        // signée automatiquement, l'utilisateur n'a pas à y penser.
        const signed = isOut ? -Math.abs(parsed) : Math.abs(parsed);
        payload.amount_cents = Math.round(signed * 100);
      } else if (method === "SINGLE_MONTH_FIXED") {
        const parsed = parseAmount(amountStr);
        if (!Number.isFinite(parsed)) {
          setSubmitError("Montant invalide. Saisissez un nombre, ex : 10000.");
          return;
        }
        if (parsed === 0) {
          setSubmitError("Le montant ne peut pas être 0.");
          return;
        }
        if (!/^\d{4}-\d{2}$/.test(singleMonth)) {
          setSubmitError("Choisissez un mois cible (format YYYY-MM).");
          return;
        }
        const signed = isOut ? -Math.abs(parsed) : Math.abs(parsed);
        payload.amount_cents = Math.round(signed * 100);
        // Le backend stocke en `date` ; on prend le 1er du mois.
        payload.start_month = `${singleMonth}-01`;
        payload.end_month = `${singleMonth}-01`;
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
      await upsertMut.mutateAsync(payload);
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

      {method !== "SINGLE_MONTH_FIXED" && cellMonth && (
        <fieldset className="space-y-1">
          <legend className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Portée de cette règle
          </legend>
          <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
            <label
              className={cn(
                "flex cursor-pointer items-start gap-2 rounded-md border px-3 py-2 transition-colors",
                scope === "from_this_month"
                  ? "border-accent/60 bg-accent/5"
                  : "border-line-soft bg-panel hover:bg-panel-2/50",
              )}
            >
              <input
                type="radio"
                name="scope"
                checked={scope === "from_this_month"}
                onChange={() => setScope("from_this_month")}
                className="mt-0.5 h-3.5 w-3.5 accent-accent"
              />
              <span className="min-w-0 flex-1">
                <span className="block text-[12.5px] font-medium text-ink">
                  À partir de ce mois
                </span>
                <span className="block text-[11.5px] text-muted-foreground">
                  S'applique à {cellMonth} et tous les suivants (jusqu'à
                  ce qu'une autre règle prenne le relais).
                </span>
              </span>
            </label>
            <label
              className={cn(
                "flex cursor-pointer items-start gap-2 rounded-md border px-3 py-2 transition-colors",
                scope === "this_month_only"
                  ? "border-accent/60 bg-accent/5"
                  : "border-line-soft bg-panel hover:bg-panel-2/50",
              )}
            >
              <input
                type="radio"
                name="scope"
                checked={scope === "this_month_only"}
                onChange={() => setScope("this_month_only")}
                className="mt-0.5 h-3.5 w-3.5 accent-accent"
              />
              <span className="min-w-0 flex-1">
                <span className="block text-[12.5px] font-medium text-ink">
                  Ce mois uniquement
                </span>
                <span className="block text-[11.5px] text-muted-foreground">
                  Exception ponctuelle qui n'affecte que {cellMonth}.
                </span>
              </span>
            </label>
          </div>
        </fieldset>
      )}

      {method === "RECURRING_FIXED" && (
        <div className="space-y-1">
          <label className="block text-[11.5px] text-ink-2">
            Montant (€){" "}
            <span className="text-muted-foreground">
              — {isOut ? "décaissement" : "encaissement"}, valeur positive
            </span>
          </label>
          <input
            type="text"
            inputMode="decimal"
            value={amountStr}
            onChange={(e) => setAmountStr(e.target.value)}
            className="w-full rounded-md border border-line-soft bg-panel px-2.5 py-1.5 text-right font-mono text-[13px] tabular-nums text-ink"
            placeholder="1500"
          />
          {previewLabel && (
            <p className="text-[11px] text-muted-foreground">
              Sera enregistré : {previewLabel}
              {isOut ? " (signe négatif appliqué automatiquement)" : ""}.
            </p>
          )}
        </div>
      )}

      {method === "SINGLE_MONTH_FIXED" && (
        <div className="space-y-3">
          <div className="space-y-1">
            <label className="block text-[11.5px] text-ink-2">
              Montant (€){" "}
              <span className="text-muted-foreground">
                — {isOut ? "décaissement" : "encaissement"}, valeur positive
              </span>
            </label>
            <input
              type="text"
              inputMode="decimal"
              value={amountStr}
              onChange={(e) => setAmountStr(e.target.value)}
              className="w-full rounded-md border border-line-soft bg-panel px-2.5 py-1.5 text-right font-mono text-[13px] tabular-nums text-ink"
              placeholder="10000"
            />
            {previewLabel && (
              <p className="text-[11px] text-muted-foreground">
                Sera enregistré : {previewLabel}
                {isOut ? " (signe négatif appliqué automatiquement)" : ""}.
              </p>
            )}
          </div>
          <div className="space-y-1">
            <label className="block text-[11.5px] text-ink-2">
              Mois d'application (un seul)
            </label>
            <MonthPicker
              value={singleMonth}
              onChange={setSingleMonth}
              placeholder="Choisir le mois"
            />
            <p className="text-[11px] text-muted-foreground">
              Le montant ne s'appliquera que sur ce mois — les autres mois
              du pivot affichent 0.
            </p>
          </div>
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

      <div className="flex items-center justify-between gap-2">
        {line ? (
          <Button
            type="button"
            variant="ghost"
            onClick={() => setConfirmDeleteOpen(true)}
            disabled={deleteMut.isPending || upsertMut.isPending}
            className="h-9 text-rose-700 hover:bg-rose-50 hover:text-rose-800"
          >
            {deleteMut.isPending ? "Suppression…" : "Supprimer la ligne"}
          </Button>
        ) : (
          <span />
        )}
        <Button
          type="submit"
          disabled={upsertMut.isPending || deleteMut.isPending}
          className="h-9"
        >
          {upsertMut.isPending ? "Enregistrement…" : "Enregistrer"}
        </Button>
      </div>

      <ConfirmDialog
        open={confirmDeleteOpen}
        title="Supprimer la ligne prévisionnelle ?"
        description={
          <>
            La cellule retombera sur le calcul par défaut (souvent 0) tant
            qu'aucune autre méthode n'est définie pour cette catégorie.
            Cette action est irréversible.
          </>
        }
        confirmLabel="Supprimer"
        tone="danger"
        busy={deleteMut.isPending}
        onConfirm={handleDeleteConfirmed}
        onCancel={() => setConfirmDeleteOpen(false)}
      />
    </form>
  );
}
