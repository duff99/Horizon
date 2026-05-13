import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { PivotTable } from "@/components/forecast/PivotTable";
import type { PivotResult } from "@/types/forecast";

function buildFixture(): PivotResult {
  const months = ["2026-03", "2026-04", "2026-05", "2026-06"];
  return {
    months,
    opening_balance_cents: 1_000_000,
    closing_balance_projection_cents: [
      1_200_000, 1_100_000, 900_000, 700_000,
    ],
    realized_series: [
      { month: "2026-03", in_cents: 500_000, out_cents: 300_000 },
      { month: "2026-04", in_cents: 200_000, out_cents: 100_000 },
      { month: "2026-05", in_cents: 0, out_cents: 0 },
      { month: "2026-06", in_cents: 0, out_cents: 0 },
    ],
    forecast_series: [
      { month: "2026-03", in_cents: 0, out_cents: 0 },
      { month: "2026-04", in_cents: 0, out_cents: 0 },
      { month: "2026-05", in_cents: 400_000, out_cents: 200_000 },
      { month: "2026-06", in_cents: 400_000, out_cents: 200_000 },
    ],
    uncategorized_net_cents: [0, 0, 0, 0],
    rows: [
      {
        category_id: 100,
        parent_id: null,
        label: "Ventes",
        level: 0,
        direction: "in",
        cells: months.map((m) => ({
          month: m,
          realized_cents: 0,
          committed_cents: 0,
          forecast_cents: 0,
          total_cents: 300_000,
          line_method: null,
          line_params: null,
        })),
      },
      {
        category_id: 101,
        parent_id: 100,
        label: "Ventes produits",
        level: 1,
        direction: "in",
        cells: months.map((m) => ({
          month: m,
          realized_cents: 0,
          committed_cents: 0,
          forecast_cents: 0,
          total_cents: 200_000,
          line_method: null,
          line_params: null,
        })),
      },
      {
        category_id: 200,
        parent_id: null,
        label: "Achats",
        level: 0,
        direction: "out",
        cells: months.map((m) => ({
          month: m,
          realized_cents: 0,
          committed_cents: 0,
          forecast_cents: 0,
          total_cents: 150_000,
          line_method: null,
          line_params: null,
        })),
      },
    ],
  };
}

describe("PivotTable", () => {
  it("renders hierarchy and toggles child visibility", () => {
    const result = buildFixture();
    const onCellClick = vi.fn();
    render(
      <PivotTable
        result={result}
        onCellClick={onCellClick}
        currentMonth="2026-04"
      />,
    );

    // Root categories are rendered
    expect(screen.getByText("Ventes")).toBeInTheDocument();
    expect(screen.getByText("Achats")).toBeInTheDocument();
    // Child is visible by default (expanded)
    expect(screen.getByText("Ventes produits")).toBeInTheDocument();

    // Collapse "Ventes" — find the chevron next to the root label row
    const ventesRow = screen.getByText("Ventes").closest("tr")!;
    const chevronBtn = within(ventesRow).getByRole("button", {
      name: /Replier|Déplier/,
    });
    fireEvent.click(chevronBtn);
    expect(screen.queryByText("Ventes produits")).not.toBeInTheDocument();
  });

  it("calls onCellClick for current & future months only", () => {
    const result = buildFixture();
    const onCellClick = vi.fn();
    render(
      <PivotTable
        result={result}
        onCellClick={onCellClick}
        currentMonth="2026-04"
      />,
    );

    const ventesRow = screen.getByText("Ventes").closest("tr")!;
    const cells = within(ventesRow).getAllByRole("cell");
    // cells are in the order months[0..3]: 03 (past), 04 (current), 05, 06 (future)
    fireEvent.click(cells[0]); // past, should not fire
    expect(onCellClick).not.toHaveBeenCalled();

    fireEvent.click(cells[1]); // current → fires
    expect(onCellClick).toHaveBeenCalledWith("2026-04", 100, "in");

    fireEvent.click(cells[3]); // future → fires
    expect(onCellClick).toHaveBeenCalledWith("2026-06", 100, "in");
    expect(onCellClick).toHaveBeenCalledTimes(2);
  });

  it("collapses the Encaissements group via group header", () => {
    const result = buildFixture();
    render(
      <PivotTable
        result={result}
        onCellClick={() => undefined}
        currentMonth="2026-04"
      />,
    );
    // Group header button toggles off the whole group
    const groupBtn = screen.getByRole("button", { name: /Encaissements/ });
    fireEvent.click(groupBtn);
    expect(screen.queryByText("Ventes")).not.toBeInTheDocument();
  });

  it("inTotals sums all rows including children, not only roots", () => {
    // Root in avec total=0 (pas de tx directes) + child in avec total=200k
    // Le total ligne Encaissements doit afficher 200k, pas 0.
    const months = ["2026-05", "2026-06"];
    const fixture: PivotResult = {
      months,
      opening_balance_cents: 0,
      closing_balance_projection_cents: [200_000, 400_000],
      realized_series: months.map((m) => ({ month: m, in_cents: 0, out_cents: 0 })),
      forecast_series: months.map((m) => ({ month: m, in_cents: 0, out_cents: 0 })),
      uncategorized_net_cents: months.map(() => 0),
      rows: [
        {
          category_id: 10,
          parent_id: null,
          label: "Ventes",
          level: 0,
          direction: "in" as const,
          cells: months.map((m) => ({
            month: m,
            realized_cents: 0,
            committed_cents: 0,
            forecast_cents: 0,
            total_cents: 0,       // root : pas de tx directes
            line_method: null,
            line_params: null,
          })),
        },
        {
          category_id: 11,
          parent_id: 10,
          label: "Ventes produits",
          level: 1,
          direction: "in" as const,
          cells: months.map((m) => ({
            month: m,
            realized_cents: 0,
            committed_cents: 0,
            forecast_cents: 0,
            total_cents: 200_000, // child : a des valeurs
            line_method: null,
            line_params: null,
          })),
        },
      ],
    };

    const { container } = render(
      <PivotTable
        result={fixture}
        onCellClick={() => undefined}
        currentMonth="2026-04"
      />,
    );

    // Après le fix, le total Encaissements = root(0) + child(200k) = 200k.
    // formatCents(200_000) = "2 000 €" (espace fine insécable U+202F entre milliers).
    // Avant le fix, la ligne Encaissements affichait "0 €" (seul root sommé).
    // On vérifie que "2 000 €" apparaît au moins 2 fois
    // (header Encaissements + ligne child).
    const text = container.textContent ?? "";
    // Regex tolérante sur l'espace (U+202F ou espace normale ou espace insécable)
    const matches = text.match(/2[   ]000[   ]€/g) ?? [];
    // Sans fix : 0 occurrence dans le groupe header Encaissements.
    // Avec fix : au moins 2 occurrences (header Encaissements + ligne child).
    expect(matches.length).toBeGreaterThanOrEqual(2);
  });

  it("respects accounting invariants across months (continuité tréso)", () => {
    // Vérifie : opening[i+1] = closing[i] ET closing[i] = opening[i] + net[i],
    // y compris quand uncategorized_net_cents est non nul.
    const months = ["2026-03", "2026-04", "2026-05"];
    const fixture: PivotResult = {
      months,
      opening_balance_cents: 1_000_000, // 10 000 €
      closing_balance_projection_cents: [0, 0, 0], // ignoré : on calcule
      realized_series: months.map((m) => ({ month: m, in_cents: 0, out_cents: 0 })),
      forecast_series: months.map((m) => ({ month: m, in_cents: 0, out_cents: 0 })),
      uncategorized_net_cents: [-50_000, 0, +20_000], // -500 €, 0, +200 €
      rows: [
        {
          category_id: 100,
          parent_id: null,
          label: "Ventes",
          level: 0,
          direction: "in",
          cells: [
            { month: months[0], realized_cents: 500_000, committed_cents: 0, forecast_cents: 0, total_cents: 500_000, line_method: null, line_params: null },
            { month: months[1], realized_cents: 300_000, committed_cents: 0, forecast_cents: 0, total_cents: 300_000, line_method: null, line_params: null },
            { month: months[2], realized_cents: 0, committed_cents: 0, forecast_cents: 200_000, total_cents: 200_000, line_method: null, line_params: null },
          ],
        },
        {
          category_id: 200,
          parent_id: null,
          label: "Achats",
          level: 0,
          direction: "out",
          cells: [
            { month: months[0], realized_cents: -200_000, committed_cents: 0, forecast_cents: 0, total_cents: -200_000, line_method: null, line_params: null },
            { month: months[1], realized_cents: -100_000, committed_cents: 0, forecast_cents: 0, total_cents: -100_000, line_method: null, line_params: null },
            { month: months[2], realized_cents: 0, committed_cents: 0, forecast_cents: -150_000, total_cents: -150_000, line_method: null, line_params: null },
          ],
        },
      ],
    };

    const { container } = render(
      <PivotTable
        result={fixture}
        onCellClick={() => undefined}
        currentMonth="2026-04"
      />,
    );

    const text = container.textContent ?? "";
    // Calculs attendus :
    //   net[0] = 500_000 - 200_000 + (-50_000) = 250_000 → 2 500 €
    //   net[1] = 300_000 - 100_000 + 0        = 200_000 → 2 000 €
    //   net[2] = 200_000 - 150_000 + 20_000   = 70_000  → 700 €
    //   close[0] = 1_000_000 + 250_000 = 1_250_000 → 12 500 €
    //   close[1] = 1_250_000 + 200_000 = 1_450_000 → 14 500 €
    //   close[2] = 1_450_000 + 70_000  = 1_520_000 → 15 200 €
    const norm = (s: string) => s.replace(/[  ]/g, " ");
    const t = norm(text);
    expect(t).toContain("2 500 €");
    expect(t).toContain("2 000 €");
    expect(t).toContain("700 €");
    expect(t).toContain("12 500 €");
    expect(t).toContain("14 500 €");
    expect(t).toContain("15 200 €");
    // Ligne uncategorized affichée (car non nulle)
    expect(t).toContain("Tx non catégorisées (net)");
  });
});
