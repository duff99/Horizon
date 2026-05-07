import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RecurringSuggestionPicker } from "@/components/forecast/RecurringSuggestionPicker";
import type { DetectedRecurrenceSuggestion } from "@/api/forecast";

const SUGGESTION_FIXTURES: DetectedRecurrenceSuggestion[] = [
  {
    counterparty_id: 10,
    counterparty_name: "Orange SA",
    average_amount: "-850.00",
    last_occurrence: "2026-04-15",
    next_expected: "2026-05-15",
    recurrence: "MONTHLY",
    occurrences_count: 6,
    entity_id: 1,
  },
  {
    counterparty_id: 20,
    counterparty_name: "EDF",
    average_amount: "-320.50",
    last_occurrence: "2026-04-01",
    next_expected: "2026-05-01",
    recurrence: "MONTHLY",
    occurrences_count: 4,
    entity_id: 1,
  },
];

function renderPicker(
  suggestions: DetectedRecurrenceSuggestion[] | null,
  { onSelect = vi.fn(), onClose = vi.fn() } = {},
) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => suggestions ?? [],
  });

  return {
    onSelect,
    onClose,
    ...render(
      <QueryClientProvider client={qc}>
        <RecurringSuggestionPicker
          entityId={1}
          onSelect={onSelect}
          onClose={onClose}
        />
      </QueryClientProvider>,
    ),
  };
}

describe("RecurringSuggestionPicker", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("affiche un état de chargement puis les suggestions", async () => {
    renderPicker(SUGGESTION_FIXTURES);
    // L'état initial montre le chargement ou les suggestions
    expect(screen.getByText("Récurrences détectées sur 6 mois")).toBeInTheDocument();
    // Attend que les données arrivent
    expect(await screen.findByText("Orange SA")).toBeInTheDocument();
    expect(await screen.findByText("EDF")).toBeInTheDocument();
  });

  it("affiche les libellés de récurrence traduits", async () => {
    renderPicker(SUGGESTION_FIXTURES);
    const labels = await screen.findAllByText("Mensuel");
    expect(labels.length).toBeGreaterThanOrEqual(1);
  });

  it("appelle onSelect avec la suggestion cliquée", async () => {
    const { onSelect } = renderPicker(SUGGESTION_FIXTURES);
    const btn = await screen.findByRole("button", { name: /Orange SA/ });
    fireEvent.click(btn);
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith(
      expect.objectContaining({ counterparty_name: "Orange SA" }),
    );
  });

  it("appelle onClose en cliquant sur Fermer", async () => {
    const { onClose } = renderPicker(SUGGESTION_FIXTURES);
    // Attendre que le rendu soit stable
    await screen.findByText("Orange SA");
    const closeBtn = screen.getByRole("button", { name: "Fermer" });
    fireEvent.click(closeBtn);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("affiche le message vide si aucune récurrence détectée", async () => {
    renderPicker([]);
    expect(
      await screen.findByText(/Aucune récurrence détectée/i),
    ).toBeInTheDocument();
  });

  it("affiche un message d'erreur si la requête échoue", async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({ detail: "Erreur serveur" }),
    });
    render(
      <QueryClientProvider client={qc}>
        <RecurringSuggestionPicker
          entityId={1}
          onSelect={vi.fn()}
          onClose={vi.fn()}
        />
      </QueryClientProvider>,
    );
    expect(
      await screen.findByText(/Impossible d'analyser l'historique/i),
    ).toBeInTheDocument();
  });
});
