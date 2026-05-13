import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type {
  ForecastLine,
  LineUpsert,
  PivotCell,
  PivotResult,
  PivotRow,
  ValidateFormulaResponse,
} from "@/types/forecast";

/**
 * Met à jour optimistiquement une ligne de pivot pour une catégorie donnée.
 *
 * Logique : pour chaque cellule future de la ligne ciblée, on recalcule
 * `forecast_cents` à partir des paramètres de la nouvelle ligne, puis
 * `total_cents = realized + committed + forecast`. Les cellules passées
 * (mois antérieurs au mois courant) ne sont jamais modifiées : leur
 * `forecast_cents` reste à 0 par convention backend (les passés sont du
 * réalisé pur).
 *
 * Méthodes supportées en optimistic : `RECURRING_FIXED` (montant fixe
 * récurrent dans la fenêtre start/end) et `SINGLE_MONTH_FIXED` (montant
 * sur un seul mois). Les autres méthodes (AVG_3M, FORMULA, etc.) sont
 * calculées côté backend et impossibles à reproduire ici sans dupliquer
 * la logique : on laisse la cellule inchangée et on compte sur un
 * éventuel refetch ultérieur pour synchroniser.
 *
 * Le mois courant est passé en paramètre (format "YYYY-MM") pour
 * déterminer le seuil passé/futur.
 */
function patchPivotWithLine(
  pivot: PivotResult,
  line: ForecastLine,
  currentMonth: string,
): PivotResult {
  const ymOf = (d: string | null): string | null =>
    d ? d.slice(0, 7) : null;
  const startYm = ymOf(line.start_month);
  const endYm = ymOf(line.end_month);
  const amount = line.amount_cents ?? 0;

  const newRows: PivotRow[] = pivot.rows.map((row) => {
    if (row.category_id !== line.category_id) return row;
    const newCells: PivotCell[] = row.cells.map((cell) => {
      if (cell.month < currentMonth) return cell;

      let newForecast: number;
      if (line.method === "RECURRING_FIXED") {
        const inWindow =
          (startYm == null || cell.month >= startYm) &&
          (endYm == null || cell.month <= endYm);
        newForecast = inWindow ? amount : 0;
      } else if (line.method === "SINGLE_MONTH_FIXED") {
        newForecast = startYm != null && cell.month === startYm ? amount : 0;
      } else {
        // Méthode calculée backend, on n'y touche pas en optimistic.
        return cell;
      }
      return {
        ...cell,
        forecast_cents: newForecast,
        total_cents: cell.realized_cents + cell.committed_cents + newForecast,
        line_method: line.method,
      };
    });
    return { ...row, cells: newCells };
  });

  return { ...pivot, rows: newRows };
}

/**
 * Optimistic update pour une suppression : remet à zéro la composante
 * forecast (et le line_method) de toutes les cellules futures de la
 * catégorie. Les cellules passées restent intactes.
 */
function patchPivotForDelete(
  pivot: PivotResult,
  categoryId: number,
  currentMonth: string,
): PivotResult {
  const newRows: PivotRow[] = pivot.rows.map((row) => {
    if (row.category_id !== categoryId) return row;
    const newCells: PivotCell[] = row.cells.map((cell) => {
      if (cell.month < currentMonth) return cell;
      return {
        ...cell,
        forecast_cents: 0,
        total_cents: cell.realized_cents + cell.committed_cents,
        line_method: null,
        line_params: null,
      };
    });
    return { ...row, cells: newCells };
  });
  return { ...pivot, rows: newRows };
}

function currentMonthYm(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export function useLines(scenarioId: number | null | undefined) {
  return useQuery({
    queryKey: ["forecast-lines", scenarioId ?? null],
    queryFn: () =>
      apiFetch<ForecastLine[]>(
        `/api/forecast/lines?scenario_id=${scenarioId}`,
      ),
    enabled: scenarioId != null,
  });
}

export function useUpsertLine() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: LineUpsert) =>
      apiFetch<ForecastLine>("/api/forecast/lines", {
        method: "PUT",
        body: JSON.stringify(payload),
      }),
    onSuccess: (line) => {
      // Pattern optimistic + background revalidation :
      // 1) Patch optimiste pour RECURRING_FIXED / SINGLE_MONTH_FIXED →
      //    feedback instantané à la fermeture du drawer.
      // 2) Invalidation systématique du pivot → refetch en arrière-plan
      //    qui réconcilie les méthodes calculées backend (AVG_*, FORMULA,
      //    BASED_ON_CATEGORY, PREVIOUS_MONTH, SAME_MONTH_LAST_YEAR) sans
      //    rechargement manuel de la page.
      const today = currentMonthYm();
      qc.setQueriesData<PivotResult>(
        { queryKey: ["forecast-pivot", line.scenario_id] },
        (old) => (old ? patchPivotWithLine(old, line, today) : old),
      );
      qc.invalidateQueries({ queryKey: ["forecast-lines", line.scenario_id] });
      qc.invalidateQueries({ queryKey: ["forecast-pivot", line.scenario_id] });
    },
  });
}

export interface DeleteLineInput {
  id: number;
  /**
   * Catégorie de la ligne à supprimer. Permet de patcher le cache pivot
   * sans avoir à le re-fetcher : on remet `forecast_cents = 0` sur toutes
   * les cellules futures de cette catégorie.
   */
  categoryId: number;
  scenarioId: number;
}

export function useDeleteLine() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: DeleteLineInput) =>
      apiFetch<void>(`/api/forecast/lines/${input.id}`, { method: "DELETE" }),
    onSuccess: (_data, input) => {
      const today = currentMonthYm();
      qc.setQueriesData<PivotResult>(
        { queryKey: ["forecast-pivot", input.scenarioId] },
        (old) => (old ? patchPivotForDelete(old, input.categoryId, today) : old),
      );
      qc.invalidateQueries({ queryKey: ["forecast-lines", input.scenarioId] });
      qc.invalidateQueries({ queryKey: ["forecast-pivot", input.scenarioId] });
    },
  });
}

export function useValidateFormula() {
  return useMutation({
    mutationFn: (payload: {
      scenario_id: number;
      formula_expr: string;
      category_id?: number | null;
    }) =>
      apiFetch<ValidateFormulaResponse>(
        "/api/forecast/lines/validate-formula",
        {
          method: "POST",
          body: JSON.stringify(payload),
        },
      ),
  });
}
