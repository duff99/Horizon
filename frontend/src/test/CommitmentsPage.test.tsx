import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { CommitmentsPage } from "../pages/CommitmentsPage";

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <CommitmentsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function mockFetch(commitments: unknown[]) {
  globalThis.fetch = vi.fn().mockImplementation((url: string) => {
    if (url.includes("/api/commitments")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({
          items: commitments,
          total: commitments.length,
          page: 1,
          per_page: 50,
        }),
      });
    }
    if (url.includes("/api/entities")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => [{ id: 1, name: "ACME", slug: "acme" }],
      });
    }
    if (url.includes("/api/categories")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => [],
      });
    }
    if (url.includes("/api/counterparties")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => [],
      });
    }
    return Promise.resolve({
      ok: true,
      status: 200,
      json: async () => [],
    });
  });
}

describe("CommitmentsPage", () => {
  beforeEach(() => {
    mockFetch([]);
  });

  it("renders the empty state when there is no commitment", async () => {
    renderPage();
    expect(
      await screen.findByText(/Aucun engagement/i),
    ).toBeInTheDocument();
  });

  it("renders the list of commitments", async () => {
    mockFetch([
      {
        id: 1,
        entity_id: 1,
        counterparty_id: 10,
        counterparty_name: "EDF",
        category_id: null,
        category_name: null,
        bank_account_id: null,
        direction: "out",
        amount_cents: 12345,
        issue_date: "2026-04-01",
        expected_date: "2026-04-15",
        status: "pending",
        matched_transaction_id: null,
        reference: "FAC-001",
        description: "Facture électricité",
        pdf_attachment_id: null,
        created_by_id: null,
        created_at: "2026-04-01T10:00:00Z",
        updated_at: "2026-04-01T10:00:00Z",
      },
    ]);
    renderPage();
    expect(await screen.findByText("EDF")).toBeInTheDocument();
    expect(screen.getByText("Facture électricité")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Matcher/i })).toBeInTheDocument();
  });
});
