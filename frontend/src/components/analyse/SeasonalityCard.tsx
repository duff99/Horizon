/**
 * SeasonalityCard — comparaison N vs N-1 par catégorie sur 24 mois (G9).
 *
 * Avec 4 mois de données disponibles en prod (janv–avril 2026), cette carte
 * affiche un placeholder informatif. Elle deviendra fonctionnelle dès 13 mois
 * de données importées.
 *
 * Placement : bas de la grille AnalysePage (col-span-12),
 * avant EntitiesComparisonTable.
 */
import { memo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useCategories } from "@/api/categories";
import { useSeasonality } from "@/api/seasonality";
import { formatCents } from "@/lib/forecastFormat";

interface Props {
  entityId?: number;
}

const MONTH_LABELS: Record<number, string> = {
  1: "Jan.", 2: "Fév.", 3: "Mar.", 4: "Avr.",
  5: "Mai", 6: "Juin", 7: "Juil.", 8: "Août",
  9: "Sep.", 10: "Oct.", 11: "Nov.", 12: "Déc.",
};

function addMonths(yyyymm: string, n: number): string {
  const [y, m] = yyyymm.split("-").map(Number);
  const date = new Date(y, m - 1 + n, 1);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

function SeasonalityCardInner({ entityId }: Props) {
  const categoriesQuery = useCategories();
  const categories = categoriesQuery.data ?? [];
  const [selectedCategoryId, setSelectedCategoryId] = useState<
    number | undefined
  >(undefined);

  const query = useSeasonality({
    entityId,
    categoryId: selectedCategoryId,
  });

  const data = query.data;

  // Calcul du mois estimé où 13 mois seront disponibles
  function estimatedDate(): string {
    if (!data?.earliest_available) return "";
    const targetMonth = addMonths(
      data.earliest_available,
      13 - (data.months_available ?? 0) - 1,
    );
    const [y, m] = targetMonth.split("-").map(Number);
    return `${MONTH_LABELS[m] ?? m} ${y}`;
  }

  // Préparer les données pour le graphique (N vs N-1)
  // On aligne les mois par month_num (1-12)
  function buildChartData() {
    if (!data?.points || data.points.length === 0) return [];
    const byMonthNum: Record<number, { n?: number; n1?: number }> = {};
    // N = année la plus récente, N-1 = année précédente
    const years = [...new Set(data.points.map((p) => p.year))].sort(
      (a, b) => b - a,
    );
    const yearN = years[0];
    const yearN1 = years[1];

    for (const pt of data.points) {
      if (!byMonthNum[pt.month_num]) byMonthNum[pt.month_num] = {};
      if (pt.year === yearN) byMonthNum[pt.month_num].n = pt.amount_cents;
      if (pt.year === yearN1) byMonthNum[pt.month_num].n1 = pt.amount_cents;
    }

    return Array.from({ length: 12 }, (_, i) => i + 1).map((monthNum) => ({
      month: MONTH_LABELS[monthNum] ?? String(monthNum),
      [`N (${yearN})`]: byMonthNum[monthNum]?.n ?? null,
      [`N-1 (${yearN1 ?? ""})`]: byMonthNum[monthNum]?.n1 ?? null,
    }));
  }

  const chartData = data?.has_enough_data ? buildChartData() : [];

  return (
    <div className="rounded-xl border border-line-soft bg-panel p-5 shadow-card">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-1.5">
            <span className="text-[15px] font-semibold text-ink">
              Saisonnalité par catégorie
            </span>
            <span
              className="cursor-help text-[11px] text-muted-foreground"
              title="Compare les flux d'une categorie mois par mois entre l'annee en cours et l'annee precedente pour detecter la saisonnalite."
            >
              ?
            </span>
          </div>
          <div className="mt-0.5 text-[12.5px] text-muted-foreground">
            Comparaison N vs N-1 par catégorie · 24 mois glissants
          </div>
        </div>

        {/* Sélecteur de catégorie */}
        <select
          className="rounded border border-line-soft bg-panel px-2 py-1 text-[13px] text-ink focus:outline-none focus:ring-1 focus:ring-blue-400"
          value={selectedCategoryId ?? ""}
          onChange={(e) =>
            setSelectedCategoryId(
              e.target.value ? Number(e.target.value) : undefined,
            )
          }
        >
          <option value="">Choisir une catégorie…</option>
          {categories.map((cat) => (
            <option key={cat.id} value={cat.id}>
              {cat.name}
            </option>
          ))}
        </select>
      </div>

      {!selectedCategoryId ? (
        <div className="flex h-[120px] items-center justify-center text-[13px] text-muted-foreground">
          Sélectionnez une catégorie pour afficher sa saisonnalité.
        </div>
      ) : query.isLoading ? (
        <div className="h-[120px] animate-pulse rounded bg-slate-100" />
      ) : query.isError ? (
        <div
          role="alert"
          className="rounded-md bg-rose-50 px-3 py-2 text-[12.5px] text-rose-900"
        >
          Impossible de charger la saisonnalité.
        </div>
      ) : !data?.has_enough_data ? (
        <div className="rounded-md bg-amber-50 px-4 py-3 text-[13px] text-amber-900">
          Données insuffisantes pour afficher la saisonnalité (
          {data?.months_available ?? 0} mois disponibles sur 13 nécessaires).
          Ce graphique sera exploitable à partir de{" "}
          <strong>{estimatedDate() || "13 mois de données importées"}</strong>.
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={260}>
          <LineChart
            data={chartData}
            margin={{ top: 4, right: 16, bottom: 4, left: 80 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="month"
              tick={{ fontSize: 11, fill: "#64748b" }}
            />
            <YAxis
              tickFormatter={(v: number) => formatCents(v)}
              tick={{ fontSize: 11, fill: "#64748b" }}
              width={80}
            />
            <Tooltip
              formatter={(v) => (typeof v === "number" ? formatCents(v) : String(v))}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            {chartData.length > 0 &&
              Object.keys(chartData[0])
                .filter((k) => k !== "month")
                .map((key, idx) => (
                  <Line
                    key={key}
                    type="monotone"
                    dataKey={key}
                    stroke={idx === 0 ? "#2563eb" : "#94a3b8"}
                    strokeWidth={idx === 0 ? 2 : 1.5}
                    strokeDasharray={idx === 1 ? "4 2" : undefined}
                    dot={false}
                    connectNulls
                  />
                ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

export const SeasonalityCard = memo(SeasonalityCardInner);
