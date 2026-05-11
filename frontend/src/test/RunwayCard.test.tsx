/**
 * Tests RunwayCard — branches d'affichage selon `status`.
 *
 * Regression couverte : un statut `"none"` (entreprise excédentaire, burn
 * rate positif côté backend) tombait dans le `default` du switch et
 * affichait "Pas assez d'historique pour calculer" — message faux pour une
 * boîte en bonne santé.
 */
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

import { RunwayCard } from "../components/analyse/RunwayCard";
import type { RunwayResponse } from "../types/analysis";

function renderCard() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <RunwayCard entityId={1} />
    </QueryClientProvider>,
  );
}

function mockRunway(payload: RunwayResponse) {
  globalThis.fetch = vi.fn().mockImplementation(() =>
    Promise.resolve({
      ok: true,
      json: async () => payload,
    }),
  );
}

describe("RunwayCard", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });
  afterEach(() => vi.restoreAllMocks());

  it("status=none -> libellé Excédentaire, pas 'Pas assez d'historique'", async () => {
    mockRunway({
      burn_rate_cents: 222449,
      current_balance_cents: 793372,
      runway_months: null,
      forecast_balance_6m_cents: [
        1015821, 1238270, 1460719, 1683168, 1905617, 2128066,
      ],
      status: "none",
    });
    renderCard();
    expect(await screen.findByText(/Excédentaire/)).toBeInTheDocument();
    expect(
      screen.queryByText(/Pas assez d'historique/),
    ).not.toBeInTheDocument();
  });

  it("status=critical -> libellé Critique avec runway en mois", async () => {
    mockRunway({
      burn_rate_cents: -41753,
      current_balance_cents: 3110,
      runway_months: 1,
      forecast_balance_6m_cents: [
        -38643, -80396, -122149, -163902, -205655, -247408,
      ],
      status: "critical",
    });
    renderCard();
    expect(await screen.findByText(/Critique/)).toBeInTheDocument();
  });
});
