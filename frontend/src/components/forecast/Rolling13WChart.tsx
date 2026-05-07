/**
 * Rolling13WChart — vue hebdomadaire court terme (W-1 à W+11, 13 semaines).
 *
 * Encaissements/décaissements réalisés (barres) + prévus (hachures) par semaine.
 * Tooltip "?" sur le titre explique l'origine des données.
 */
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Cell,
} from "recharts";
import { useRolling13W } from "@/api/treasury";

const EUR = new Intl.NumberFormat("fr-FR", {
  maximumFractionDigits: 0,
  signDisplay: "auto",
});

function formatEUR(cents: number): string {
  return `${EUR.format(cents / 100)} €`;
}

interface Props {
  entityId: number;
  scenarioId?: number | null;
}

export function Rolling13WChart({ entityId, scenarioId }: Props) {
  const q = useRolling13W({ entityId, scenarioId });

  if (q.isLoading) {
    return (
      <div className="h-[220px] animate-pulse rounded-lg bg-panel-2/40" />
    );
  }

  if (!q.data || q.data.points.length === 0) {
    return (
      <div className="rounded-md bg-panel-2/40 px-4 py-6 text-center text-[13px] text-muted-foreground">
        Aucune donnée disponible pour la vue hebdomadaire.
      </div>
    );
  }

  const data = q.data.points.map((p) => ({
    label: p.week_label,
    realized: p.realized_cents / 100,
    forecast: p.forecast_cents / 100,
    isPast: p.is_past,
  }));

  return (
    <div>
      <div className="mb-2 flex items-center gap-1.5">
        <h3 className="text-[13px] font-semibold text-ink">
          Trésorerie hebdomadaire — 13 semaines glissantes (W-1 à W+11)
        </h3>
        <span
          title="Vue semaine par semaine : encaissements et décaissements réalisés (semaines passées) et prévus (semaines futures)."
          className="cursor-help text-[11px] text-muted-foreground"
        >
          ?
        </span>
      </div>
      <div className="flex items-center gap-4 mb-2 text-[11px] text-muted-foreground">
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-3 rounded-sm bg-emerald-600" />
          Encaissements réalisés
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-3 rounded-sm bg-rose-500" />
          Décaissements réalisés
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-3 rounded-sm bg-sky-400 opacity-60" />
          Flux prévus (scénario)
        </span>
      </div>
      <div style={{ width: "100%", height: 220 }}>
        <ResponsiveContainer>
          <ComposedChart
            data={data}
            margin={{ top: 8, right: 8, bottom: 8, left: 0 }}
          >
            <CartesianGrid
              strokeDasharray="2 2"
              stroke="hsl(var(--line))"
              vertical={false}
            />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 10, fill: "hsl(var(--muted-fg))" }}
              axisLine={{ stroke: "hsl(var(--line))" }}
              tickLine={false}
              interval={0}
              angle={-30}
              textAnchor="end"
              height={40}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "hsl(var(--muted-fg))" }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => EUR.format(Number(v))}
              width={68}
            />
            <Tooltip
              contentStyle={{
                background: "hsl(var(--panel))",
                border: "1px solid hsl(var(--line))",
                borderRadius: 8,
                fontSize: 12,
              }}
              formatter={(value, name) => {
                const cents = Math.round(Number(value) * 100);
                const labels: Record<string, string> = {
                  realized: "Réalisé net",
                  forecast: "Prévu (scénario)",
                };
                return [formatEUR(cents), labels[String(name)] ?? String(name)];
              }}
              labelFormatter={(l) => String(l)}
            />
            <Bar dataKey="realized" name="realized" maxBarSize={22} radius={[3, 3, 0, 0]}>
              {data.map((entry, i) => (
                <Cell
                  key={i}
                  fill={
                    entry.realized >= 0
                      ? "hsl(152 48% 42%)"
                      : "hsl(354 60% 52%)"
                  }
                  opacity={entry.isPast ? 1 : 0.5}
                />
              ))}
            </Bar>
            <Bar
              dataKey="forecast"
              name="forecast"
              fill="hsl(199 89% 48%)"
              maxBarSize={22}
              radius={[3, 3, 0, 0]}
              opacity={0.6}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
