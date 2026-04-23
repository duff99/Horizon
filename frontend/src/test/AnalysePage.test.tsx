import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

import { AnalysePage } from "../pages/AnalysePage";
import type {
  CategoryDriftResponse,
  ClientConcentrationResponse,
  EntitiesComparisonResponse,
  RunwayResponse,
  TopMoversResponse,
  YoYResponse,
} from "../types/analysis";

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AnalysePage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const drift: CategoryDriftResponse = {
  seuil_pct: 20,
  rows: [
    {
      category_id: 1,
      label: "Loyer",
      current_cents: 150000,
      avg3m_cents: 120000,
      delta_cents: 30000,
      delta_pct: 25,
      status: "alert",
    },
    {
      category_id: 2,
      label: "Salaires",
      current_cents: 500000,
      avg3m_cents: 495000,
      delta_cents: 5000,
      delta_pct: 1,
      status: "normal",
    },
  ],
};

const movers: TopMoversResponse = {
  increases: [
    {
      category_id: 1,
      label: "Ventes SaaS",
      direction: "in",
      delta_cents: 200000,
      sparkline_3m_cents: [100000, 150000, 180000],
    },
  ],
  decreases: [
    {
      category_id: 2,
      label: "Frais bancaires",
      direction: "out",
      delta_cents: -80000,
      sparkline_3m_cents: [50000, 40000, 30000],
    },
  ],
};

const runway: RunwayResponse = {
  burn_rate_cents: -50000,
  current_balance_cents: 600000,
  runway_months: 12,
  forecast_balance_6m_cents: [600000, 550000, 500000, 450000, 400000, 350000],
  status: "ok",
};

const yoy: YoYResponse = {
  months: ["2025-05", "2025-06", "2026-04"],
  series: [
    {
      month: "2025-05",
      revenues_current: 200000,
      revenues_previous: 180000,
      expenses_current: 100000,
      expenses_previous: 90000,
    },
    {
      month: "2025-06",
      revenues_current: 220000,
      revenues_previous: 200000,
      expenses_current: 110000,
      expenses_previous: 100000,
    },
    {
      month: "2026-04",
      revenues_current: 260000,
      revenues_previous: 200000,
      expenses_current: 130000,
      expenses_previous: 105000,
    },
  ],
};

const concentration: ClientConcentrationResponse = {
  total_revenue_cents: 1000000,
  top5: [
    { counterparty_id: 1, name: "Client A", amount_cents: 400000, share_pct: 40 },
    { counterparty_id: 2, name: "Client B", amount_cents: 300000, share_pct: 30 },
    { counterparty_id: 3, name: "Client C", amount_cents: 150000, share_pct: 15 },
    { counterparty_id: 4, name: "Client D", amount_cents: 80000, share_pct: 8 },
    { counterparty_id: 5, name: "Client E", amount_cents: 50000, share_pct: 5 },
  ],
  others_cents: 20000,
  others_share_pct: 2,
  hhi: 2854,
  risk_level: "high",
};

const comparison: EntitiesComparisonResponse = {
  entities: [
    {
      entity_id: 1,
      name: "ACREED SAS",
      revenues_cents: 1000000,
      expenses_cents: 800000,
      net_variation_cents: 200000,
      current_balance_cents: 500000,
      burn_rate_cents: -50000,
      runway_months: 10,
    },
    {
      entity_id: 2,
      name: "ACREED SCI",
      revenues_cents: 200000,
      expenses_cents: 150000,
      net_variation_cents: 50000,
      current_balance_cents: 300000,
      burn_rate_cents: 10000,
      runway_months: null,
    },
  ],
};

describe("AnalysePage", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      const s = String(url);
      return Promise.resolve({
        ok: true,
        json: async () => {
          if (s.includes("/api/analysis/category-drift")) return drift;
          if (s.includes("/api/analysis/top-movers")) return movers;
          if (s.includes("/api/analysis/runway")) return runway;
          if (s.includes("/api/analysis/yoy")) return yoy;
          if (s.includes("/api/analysis/client-concentration"))
            return concentration;
          if (s.includes("/api/analysis/entities-comparison")) return comparison;
          if (s.includes("/api/entities")) return [];
          return {};
        },
      });
    });
  });

  afterEach(() => vi.restoreAllMocks());

  it("renders the page header and the six widgets", async () => {
    renderPage();
    expect(
      screen.getByRole("heading", { level: 1, name: /Analyse/i }),
    ).toBeInTheDocument();

    // Chaque widget doit apparaître au moins une fois (titre du card).
    expect(
      await screen.findByText(/Dérives par catégorie/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/Top mouvements/i)).toBeInTheDocument();
    expect(screen.getByText(/^Runway$/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Comparaison année \/ année/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/Concentration clients/i)).toBeInTheDocument();
    expect(screen.getByText(/Comparaison des sociétés/i)).toBeInTheDocument();
  });

  it("renders alert row for drift category beyond threshold", async () => {
    renderPage();
    expect(await screen.findByText("Loyer")).toBeInTheDocument();
    // Badge "Dérive" (singulier) attendu pour la ligne alerte.
    // Note : le header "Dérives par catégorie" est au pluriel donc ne matche pas.
    const badges = await screen.findAllByText(/^Dérive$/);
    expect(badges.length).toBeGreaterThan(0);
  });

  it("hides entities comparison widget when only one entity is accessible", async () => {
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      const s = String(url);
      return Promise.resolve({
        ok: true,
        json: async () => {
          if (s.includes("/api/analysis/category-drift")) return drift;
          if (s.includes("/api/analysis/top-movers")) return movers;
          if (s.includes("/api/analysis/runway")) return runway;
          if (s.includes("/api/analysis/yoy")) return yoy;
          if (s.includes("/api/analysis/client-concentration"))
            return concentration;
          if (s.includes("/api/analysis/entities-comparison"))
            return { entities: [comparison.entities[0]] };
          if (s.includes("/api/entities")) return [];
          return {};
        },
      });
    });
    renderPage();
    // Attendre que la query entities-comparison se résolve et que le widget disparaisse.
    await waitFor(() => {
      expect(screen.queryByText(/Comparaison des sociétés/i)).toBeNull();
    });
  });
});
