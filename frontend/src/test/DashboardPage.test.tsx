import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { DashboardPage } from "../pages/DashboardPage";
import type { DashboardSummary } from "../types/api";

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function mockSummary(overrides: Partial<DashboardSummary> = {}): DashboardSummary {
  return {
    period: "current_month",
    period_label: "Avril 2026",
    period_start: "2026-04-01",
    period_end: "2026-04-19",
    total_balance: "1234.56",
    total_balance_asof: "2026-04-18",
    inflows: "2500.00",
    outflows: "-800.50",
    uncategorized_count: 3,
    daily: [
      { date: "2026-04-01", inflows: "1000.00", outflows: "-200.00" },
      { date: "2026-04-02", inflows: "1500.00", outflows: "-600.50" },
    ],
    ...overrides,
  };
}

describe("DashboardPage", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      const s = String(url);
      return Promise.resolve({
        ok: true,
        json: async () => {
          if (s.includes("period=previous_month")) {
            return mockSummary({
              period: "previous_month",
              period_label: "Mars 2026",
              inflows: "9999.00",
            });
          }
          return mockSummary();
        },
      });
    });
  });

  afterEach(() => vi.restoreAllMocks());

  it("displays the current-month KPIs from the summary", async () => {
    renderPage();
    expect(await screen.findByText(/Période\s*:\s*Avril 2026/i)).toBeInTheDocument();
    expect(screen.getByText(/1[\s\u00a0]234,56/)).toBeInTheDocument(); // total_balance
    expect(screen.getByText(/2[\s\u00a0]500,00/)).toBeInTheDocument(); // inflows
    expect(screen.getByText("3")).toBeInTheDocument(); // uncategorized
  });

  it("refetches when period changes", async () => {
    renderPage();
    await screen.findByText(/Avril 2026/i);

    await userEvent.click(screen.getByRole("tab", { name: /Mois précédent/i }));

    expect(await screen.findByText(/Mars 2026/i)).toBeInTheDocument();
    expect(screen.getByText(/9[\s\u00a0]999,00/)).toBeInTheDocument();
  });

  it("shows an empty state when no daily data", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockSummary({ daily: [] }),
    });
    renderPage();
    expect(
      await screen.findByText(/Aucune transaction sur cette période/i),
    ).toBeInTheDocument();
  });

  it("surfaces a fetch error", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false, status: 500 });
    renderPage();
    expect(await screen.findByRole("alert")).toHaveTextContent(/Erreur/i);
  });
});
