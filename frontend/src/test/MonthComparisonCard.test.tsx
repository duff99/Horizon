import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("@/api/dashboardComparison", () => ({
  useMonthComparison: () => ({
    data: {
      current: {
        month_label: "avr. 2026",
        in_cents: 14_500_000,
        out_cents: -13_800_000,
      },
      previous: {
        month_label: "mars 2026",
        in_cents: 14_763_500,
        out_cents: -12_070_300,
      },
    },
    isLoading: false,
    isError: false,
  }),
}));

import { MonthComparisonCard } from "@/components/dashboard/MonthComparisonCard";

function renderCard() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MonthComparisonCard entityId={null} />
    </QueryClientProvider>,
  );
}

describe("MonthComparisonCard", () => {
  it("renders the title and both month labels", () => {
    renderCard();
    expect(
      screen.getByText(/Réalisé mois en cours vs mois précédent/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Comparaison de avr\. 2026 à mars 2026/i),
    ).toBeInTheDocument();
    // Legend entries
    expect(screen.getAllByText(/avr\. 2026/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/mars 2026/i).length).toBeGreaterThan(0);
  });
});
