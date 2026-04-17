import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { ImportHistoryPage } from "../pages/ImportHistoryPage";

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ImportHistoryPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ImportHistoryPage", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [
        {
          id: "1", bank_account_id: "ba1", bank_code: "delubac",
          status: "completed", filename: "janv.pdf",
          imported_count: 25, duplicates_skipped: 2,
          counterparties_pending_created: 3,
          created_at: "2026-04-16T10:00:00",
        },
      ],
    });
  });

  it("displays imports in a table", async () => {
    renderPage();
    expect(await screen.findByText("janv.pdf")).toBeInTheDocument();
    expect(screen.getByText("25")).toBeInTheDocument();
    expect(screen.getByText(/Terminé/i)).toBeInTheDocument();
  });
});
