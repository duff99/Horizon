import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CellEditorDrawer } from "@/components/forecast/CellEditorDrawer";

function renderDrawer(onClose = vi.fn()) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return {
    onClose,
    ...render(
      <QueryClientProvider client={qc}>
        <CellEditorDrawer
          open
          month="2026-04"
          categoryId={101}
          entityId={1}
          scenarioId={42}
          accountIds={null}
          onClose={onClose}
        />
      </QueryClientProvider>,
    ),
  };
}

function mockFetch() {
  globalThis.fetch = vi.fn().mockImplementation((url: string) => {
    if (url.includes("/api/categories")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => [{ id: 101, name: "Ventes", slug: "sales", parent_category_id: null }],
      });
    }
    if (url.includes("/api/forecast/lines")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => [],
      });
    }
    if (url.includes("/api/transactions")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({ items: [], total: 0, page: 1, per_page: 200 }),
      });
    }
    if (url.includes("/api/commitments")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({ items: [], total: 0, page: 1, per_page: 50 }),
      });
    }
    return Promise.resolve({
      ok: true,
      status: 200,
      json: async () => [],
    });
  });
}

describe("CellEditorDrawer", () => {
  beforeEach(() => {
    mockFetch();
  });

  it("renders the month + category name header", async () => {
    renderDrawer();
    expect(await screen.findByText("Ventes")).toBeInTheDocument();
    // "Avril 2026" (long format) — case-insensitive match
    expect(
      screen.getByText(/avril 2026/i),
    ).toBeInTheDocument();
  });

  it("switches tabs and renders the matching empty state", async () => {
    renderDrawer();
    // Default tab is Prévisionnel which renders MethodForm (radio group)
    expect(
      await screen.findByText(/Méthode de calcul/i),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Payées" }));
    expect(
      await screen.findByText(/Aucune transaction payée/i),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Engagées" }));
    expect(
      await screen.findByText(/Aucun engagement en attente/i),
    ).toBeInTheDocument();
  });

  it("calls onClose when clicking the close button", async () => {
    const { onClose } = renderDrawer();
    const btn = await screen.findByRole("button", { name: "Fermer" });
    fireEvent.click(btn);
    expect(onClose).toHaveBeenCalled();
  });
});
