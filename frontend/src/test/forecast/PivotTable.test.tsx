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
    expect(onCellClick).toHaveBeenCalledWith("2026-04", 100);

    fireEvent.click(cells[3]); // future → fires
    expect(onCellClick).toHaveBeenCalledWith("2026-06", 100);
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
});
