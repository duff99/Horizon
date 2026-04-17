import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { CounterpartiesPage } from "../pages/CounterpartiesPage";

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <CounterpartiesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("CounterpartiesPage", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn().mockImplementation((_url: string, opts: any = {}) => {
      if ((opts.method ?? "GET") === "GET") {
        return Promise.resolve({
          ok: true,
          json: async () => [
            { id: 1, entity_id: 1, name: "ACME", status: "pending" },
          ],
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({ id: 1, entity_id: 1, name: "ACME", status: "active" }),
      });
    });
  });

  it("lists pending counterparties and activates one", async () => {
    renderPage();
    expect(await screen.findByText("ACME")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /^valider$/i }));
    await waitFor(() => {
      expect((globalThis.fetch as any).mock.calls.some(
        ([u, o]: any[]) => u.startsWith("/api/counterparties/1") && o.method === "PATCH"
      )).toBe(true);
    });
  });
});
