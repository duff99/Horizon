import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

import { AnalysePage } from "../pages/AnalysePage";
import type {
  CategoryDriftResponse,
  ClientConcentrationResponse,
  EntitiesComparisonResponse,
  MoMResponse,
  RunwayResponse,
  TopMoversResponse,
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

const mom: MoMResponse = {
  months: ["2025-11", "2025-12", "2026-01", "2026-02", "2026-03", "2026-04"],
  series: [
    {
      month: "2025-11",
      revenues_cents: 200000,
      expenses_cents: 100000,
      net_cents: 100000,
      delta_revenues_pct: null,
      delta_expenses_pct: null,
    },
    {
      month: "2025-12",
      revenues_cents: 220000,
      expenses_cents: 110000,
      net_cents: 110000,
      delta_revenues_pct: 10.0,
      delta_expenses_pct: 10.0,
    },
    {
      month: "2026-01",
      revenues_cents: 210000,
      expenses_cents: 105000,
      net_cents: 105000,
      delta_revenues_pct: -4.55,
      delta_expenses_pct: -4.55,
    },
    {
      month: "2026-02",
      revenues_cents: 230000,
      expenses_cents: 115000,
      net_cents: 115000,
      delta_revenues_pct: 9.52,
      delta_expenses_pct: 9.52,
    },
    {
      month: "2026-03",
      revenues_cents: 240000,
      expenses_cents: 120000,
      net_cents: 120000,
      delta_revenues_pct: 4.35,
      delta_expenses_pct: 4.35,
    },
    {
      month: "2026-04",
      revenues_cents: 260000,
      expenses_cents: 130000,
      net_cents: 130000,
      delta_revenues_pct: 8.33,
      delta_expenses_pct: 8.33,
    },
  ],
  available_months: 6,
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
          if (s.includes("/api/analysis/mom")) return mom;
          if (s.includes("/api/analysis/client-concentration"))
            return concentration;
          if (s.includes("/api/analysis/entities-comparison")) return comparison;
          if (s.includes("/api/entities")) return [];
          if (s.includes("/api/categories")) return [];
          if (s.includes("/api/anomalies")) return { entity_id: 1, days_analyzed: 180, anomaly_count: 0, rows: [] };
          if (s.includes("/api/analysis/working-capital")) return { dso_days: null, dpo_days: null, bfr_cents: null, receivables_cents: 0, payables_cents: 0, matched_in_count: 0, matched_out_count: 0, has_data: false };
          if (s.includes("/api/analysis/forecast-variance")) return { points: [], has_forecast: false };
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
      screen.getByText(/Tendance mensuelle/i),
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
          if (s.includes("/api/analysis/mom")) return mom;
          if (s.includes("/api/analysis/client-concentration"))
            return concentration;
          if (s.includes("/api/analysis/entities-comparison"))
            return { entities: [comparison.entities[0]] };
          if (s.includes("/api/entities")) return [];
          if (s.includes("/api/categories")) return [];
          if (s.includes("/api/anomalies")) return { entity_id: 1, days_analyzed: 180, anomaly_count: 0, rows: [] };
          if (s.includes("/api/analysis/working-capital")) return { dso_days: null, dpo_days: null, bfr_cents: null, receivables_cents: 0, payables_cents: 0, matched_in_count: 0, matched_out_count: 0, has_data: false };
          if (s.includes("/api/analysis/forecast-variance")) return { points: [], has_forecast: false };
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
