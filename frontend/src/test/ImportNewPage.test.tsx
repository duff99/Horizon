import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { ImportNewPage } from "../pages/ImportNewPage";

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ImportNewPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ImportNewPage", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.startsWith("/api/bank-accounts")) {
        return Promise.resolve({
          ok: true,
          json: async () => [{ id: 1, iban: "FR76...", name: "Compte 1", entity_id: 1 }],
        });
      }
      if (url === "/api/imports" && (globalThis.fetch as any).mock.calls.length > 0) {
        return Promise.resolve({
          ok: true,
          status: 201,
          json: async () => ({
            id: "imp1", status: "completed", imported_count: 3,
            duplicates_skipped: 0, counterparties_pending_created: 1,
          }),
        });
      }
      return Promise.resolve({ ok: true, json: async () => [] });
    });
  });

  it("displays page title in French", async () => {
    renderPage();
    expect(await screen.findByText(/importer un relevé/i)).toBeInTheDocument();
  });

  it("displays success summary after upload", async () => {
    renderPage();
    await screen.findByText(/Compte 1/);
    fireEvent.change(screen.getByTestId("bank-account-select"), {
      target: { value: "1" },
    });
    const file = new File([new Uint8Array([1])], "x.pdf", { type: "application/pdf" });
    const input = screen.getByTestId("file-dropzone").querySelector("input") as HTMLInputElement;
    Object.defineProperty(input, "files", { value: [file] });
    fireEvent.change(input);
    await waitFor(() => {
      expect(screen.getByText(/3 transaction/i)).toBeInTheDocument();
    });
  });
});
