import { describe, it, expect, vi, beforeEach } from "vitest";
import { fetchImports, uploadImport } from "../api/imports";
import { fetchTransactions } from "../api/transactions";
import { updateCounterparty } from "../api/counterparties";

describe("API clients Plan 1", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  it("fetchImports calls GET /api/imports", async () => {
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => [],
    });
    await fetchImports();
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/imports",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("uploadImport POSTs multipart with file", async () => {
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({ id: 1, status: "completed" }),
    });
    const file = new File([new Uint8Array([1, 2])], "x.pdf", { type: "application/pdf" });
    await uploadImport({ bankAccountId: 42, file });
    const call = (globalThis.fetch as any).mock.calls[0];
    expect(call[0]).toBe("/api/imports");
    expect(call[1].method).toBe("POST");
    expect(call[1].body).toBeInstanceOf(FormData);
  });

  it("fetchTransactions serialises filters as query params", async () => {
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ items: [], total: 0, page: 1, per_page: 50 }),
    });
    await fetchTransactions({ bank_account_id: 42, page: 2 });
    const url = (globalThis.fetch as any).mock.calls[0][0];
    expect(url).toContain("bank_account_id=42");
    expect(url).toContain("page=2");
  });

  it("updateCounterparty PATCHes with JSON body", async () => {
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ id: 1, status: "active", name: "X", entity_id: 7 }),
    });
    await updateCounterparty(1, { status: "active" });
    const call = (globalThis.fetch as any).mock.calls[0];
    expect(call[1].method).toBe("PATCH");
    expect(call[1].headers["Content-Type"]).toBe("application/json");
  });
});
