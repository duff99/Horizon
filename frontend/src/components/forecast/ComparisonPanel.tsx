import { useMemo, useState } from "react";

import {
  useForecastComparison,
  useReCloseSnapshot,
  type ComparisonMonth,
  type ComparisonRow,
} from "@/api/forecastComparison";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { formatCents, formatMonthLabel } from "@/lib/forecastFormat";
import { cn } from "@/lib/utils";

interface Props {
  scenarioId: number | null;
  entityId: number | null;
  from: string;
  to: string;
}

const STATUS_COLOR: Record<ComparisonRow["status"], string> = {
  green: "text-emerald-700",
  amber: "text-amber-700",
  red: "text-rose-700",
  "no-forecast": "text-muted-foreground",
};

function StatusDot({ status }: { status: ComparisonRow["status"] }) {
  const bg =
    status === "green"
      ? "bg-emerald-500"
      : status === "amber"
        ? "bg-amber-500"
        : status === "red"
          ? "bg-rose-500"
          : "bg-muted-foreground/40";
  return (
    <span
      aria-hidden
      className={cn("inline-block h-2 w-2 shrink-0 rounded-full", bg)}
    />
  );
}

function formatEcartPct(pct: number | null): string {
  if (pct == null) return "—";
  return `${pct.toFixed(1)} %`;
}

export function ComparisonPanel({ scenarioId, entityId, from, to }: Props) {
  const { data, isLoading, error } = useForecastComparison({
    scenarioId,
    entityId,
    from,
    to,
  });
  const reCloseMut = useReCloseSnapshot();
  const [confirmMonth, setConfirmMonth] = useState<string | null>(null);

  const closedMonths = useMemo(
    () => (data?.months ?? []).filter((m) => m.is_snapshotted),
    [data],
  );

  if (isLoading) {
    return (
      <div className="rounded-xl border border-line-soft bg-panel p-6 text-center text-[12.5px] text-muted-foreground shadow-card">
        Chargement de la comparaison…
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-[12.5px] text-rose-900 shadow-card">
        Erreur de chargement : {String(error)}
      </div>
    );
  }

  if (closedMonths.length === 0) {
    return (
      <div className="rounded-xl border border-line-soft bg-panel p-6 text-center text-[12.5px] text-muted-foreground shadow-card">
        <p className="mb-1 text-[13px] font-medium text-ink">
          Aucun mois clôturé sur la plage sélectionnée.
        </p>
        <p>
          Le suivi des écarts compare ce qui était prévu (snapshot pris au
          passage du mois) au réalisé importé. Aucun snapshot disponible
          pour l'instant : élargis la plage vers des mois passés, ou
          attends qu'un mois prévu bascule en passé.
        </p>
      </div>
    );
  }

  function handleReClose(month: string) {
    if (scenarioId == null || entityId == null) return;
    reCloseMut.mutate(
      { scenario_id: scenarioId, entity_id: entityId, month },
      { onSettled: () => setConfirmMonth(null) },
    );
  }

  return (
    <div className="space-y-4">
      {closedMonths.map((m) => (
        <MonthCard
          key={m.month}
          month={m}
          onReClose={() => setConfirmMonth(m.month)}
        />
      ))}

      <ConfirmDialog
        open={confirmMonth != null}
        title={`Re-clôturer ${
          confirmMonth ? formatMonthLabel(confirmMonth, "long") : ""
        } ?`}
        description={
          <>
            Le snapshot existant sera remplacé par les valeurs prévues
            actuelles de toutes les catégories. Utile si tu as ajouté des
            règles prévisionnelles après la première clôture. Cette
            action n'efface pas les transactions importées.
          </>
        }
        confirmLabel="Re-clôturer"
        busy={reCloseMut.isPending}
        onConfirm={() => confirmMonth && handleReClose(confirmMonth)}
        onCancel={() => setConfirmMonth(null)}
      />
    </div>
  );
}

function MonthCard({
  month,
  onReClose,
}: {
  month: ComparisonMonth;
  onReClose: () => void;
}) {
  const inRows = month.rows.filter((r) => r.direction === "in");
  const outRows = month.rows.filter((r) => r.direction === "out");

  return (
    <div className="overflow-hidden rounded-xl border border-line-soft bg-panel shadow-card">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-line-soft bg-panel-2/40 px-5 py-3">
        <div>
          <h3 className="text-[14px] font-semibold text-ink">
            {formatMonthLabel(month.month, "long")}
          </h3>
          <p className="text-[11.5px] text-muted-foreground">
            Comparaison entre les valeurs prévues figées et les transactions
            réellement importées.
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onReClose}
          className="h-8"
        >
          Re-clôturer ce mois
        </Button>
      </header>

      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse text-[12.5px]">
          <thead className="bg-panel-2/70 text-[11px] uppercase tracking-wider text-muted-foreground">
            <tr>
              <th className="px-4 py-2 text-left">Catégorie</th>
              <th className="whitespace-nowrap px-3 py-2 text-right">Prévu</th>
              <th className="whitespace-nowrap px-3 py-2 text-right">Réalisé</th>
              <th className="whitespace-nowrap px-3 py-2 text-right">Écart €</th>
              <th className="whitespace-nowrap px-3 py-2 text-right">Écart %</th>
            </tr>
          </thead>
          <tbody>
            <SectionHeader label="Encaissements" />
            {inRows.length === 0 ? (
              <tr>
                <td
                  colSpan={5}
                  className="px-4 py-2 text-[12px] text-muted-foreground"
                >
                  Aucun encaissement prévu ni réalisé.
                </td>
              </tr>
            ) : (
              inRows.map((r) => <ComparisonRowView key={r.category_id} row={r} />)
            )}
            <TotalRow
              label="Total encaissements"
              forecast={month.total_in_forecast_cents}
              realized={month.total_in_realized_cents}
            />

            <SectionHeader label="Décaissements" />
            {outRows.length === 0 ? (
              <tr>
                <td
                  colSpan={5}
                  className="px-4 py-2 text-[12px] text-muted-foreground"
                >
                  Aucun décaissement prévu ni réalisé.
                </td>
              </tr>
            ) : (
              outRows.map((r) => <ComparisonRowView key={r.category_id} row={r} />)
            )}
            <TotalRow
              label="Total décaissements"
              forecast={month.total_out_forecast_cents}
              realized={month.total_out_realized_cents}
            />

            <TotalRow
              label="Variation nette"
              forecast={month.net_forecast_cents}
              realized={month.net_realized_cents}
              emphasized
            />
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SectionHeader({ label }: { label: string }) {
  return (
    <tr>
      <th
        colSpan={5}
        className="border-y border-line-soft bg-panel-2/30 px-4 py-1.5 text-left text-[11px] font-semibold uppercase tracking-wider text-ink-2"
      >
        {label}
      </th>
    </tr>
  );
}

function ComparisonRowView({ row }: { row: ComparisonRow }) {
  return (
    <tr className="border-t border-line-soft hover:bg-panel-2/30">
      <th
        scope="row"
        className="px-4 py-1.5 text-left font-normal text-ink"
      >
        <span className="inline-flex items-center gap-2">
          <StatusDot status={row.status} />
          <span className="truncate">{row.label}</span>
        </span>
      </th>
      <td className="whitespace-nowrap px-3 py-1.5 text-right font-mono tabular-nums text-ink-2">
        {row.forecast_cents === 0 ? "—" : formatCents(row.forecast_cents)}
      </td>
      <td className="whitespace-nowrap px-3 py-1.5 text-right font-mono tabular-nums text-ink">
        {formatCents(row.realized_cents)}
      </td>
      <td
        className={cn(
          "whitespace-nowrap px-3 py-1.5 text-right font-mono tabular-nums",
          STATUS_COLOR[row.status],
        )}
      >
        {formatCents(row.ecart_cents)}
      </td>
      <td
        className={cn(
          "whitespace-nowrap px-3 py-1.5 text-right font-mono tabular-nums",
          STATUS_COLOR[row.status],
        )}
      >
        {formatEcartPct(row.ecart_pct)}
      </td>
    </tr>
  );
}

function TotalRow({
  label,
  forecast,
  realized,
  emphasized = false,
}: {
  label: string;
  forecast: number;
  realized: number;
  emphasized?: boolean;
}) {
  const ecart = realized - forecast;
  // Pour les totaux on simplifie : >10% = ambre, >25% = rouge, sinon vert.
  // Pas de status "no-forecast" sur les totaux (forecast=0 implique réalité
  // imprévue totale, mais reste informatif).
  const pct =
    forecast === 0 ? null : (Math.abs(ecart) / Math.abs(forecast)) * 100;
  const color =
    pct == null
      ? "text-muted-foreground"
      : pct < 10
        ? "text-emerald-700"
        : pct < 25
          ? "text-amber-700"
          : "text-rose-700";

  return (
    <tr
      className={cn(
        "border-t border-line-soft",
        emphasized ? "bg-panel-2/60 font-medium" : "bg-panel-2/30",
      )}
    >
      <th scope="row" className="px-4 py-2 text-left text-[12.5px] text-ink">
        {label}
      </th>
      <td className="whitespace-nowrap px-3 py-2 text-right font-mono tabular-nums text-ink-2">
        {forecast === 0 ? "—" : formatCents(forecast)}
      </td>
      <td className="whitespace-nowrap px-3 py-2 text-right font-mono tabular-nums text-ink">
        {formatCents(realized)}
      </td>
      <td className={cn("whitespace-nowrap px-3 py-2 text-right font-mono tabular-nums", color)}>
        {formatCents(ecart)}
      </td>
      <td className={cn("whitespace-nowrap px-3 py-2 text-right font-mono tabular-nums", color)}>
        {formatEcartPct(pct)}
      </td>
    </tr>
  );
}
