import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { TransactionsPage } from "../pages/TransactionsPage";

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <TransactionsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("TransactionsPage", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        items: [
          {
            id: "t1", operation_date: "2026-01-10", value_date: "2026-01-10",
            label: "VIR SEPA ACME", raw_label: "VIR SEPA ACME",
            amount: "-42.50", is_aggregation_parent: false,
            parent_transaction_id: null, counterparty: null, category: null,
          },
        ],
        total: 1, page: 1, per_page: 50,
      }),
    });
  });

  it("displays transactions in a French table", async () => {
    renderPage();
    expect(await screen.findByText("VIR SEPA ACME")).toBeInTheDocument();
    expect(screen.getByText("-42,50 €")).toBeInTheDocument();
  });
});
