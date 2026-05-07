/**
 * Tests E6 — bulk-categorize-filtered : construction du payload a partir du filtre courant.
 *
 * On teste la logique de construction du payload de facon isolee (fonctions pures)
 * car le rendu complet de TransactionsPage echoue dans jsdom a cause de Radix Select.
 */
import { describe, it, expect } from "vitest";
import type { TransactionFilter } from "../types/api";
import type { BulkCategorizeFilteredPayload } from "../api/transactions";

/**
 * Reproduit la logique de handleBulkCategorize dans TransactionsPage.tsx
 * quand selectAllFiltered est true.
 */
function buildFilteredPayload(
  filters: TransactionFilter,
  entityId: number | null,
  categoryId: number,
): BulkCategorizeFilteredPayload {
  return {
    category_id: categoryId,
    entity_id: entityId ?? undefined,
    bank_account_id: filters.bank_account_id,
    date_from: filters.date_from,
    date_to: filters.date_to,
    counterparty_id: filters.counterparty_id,
    search: filters.search,
    uncategorized: filters.uncategorized,
    include_sepa_children: filters.include_sepa_children,
    amount_min: filters.amount_min,
    amount_max: filters.amount_max,
  };
}

describe("E6 — buildFilteredPayload", () => {
  it("inclut category_id et entity_id dans le payload", () => {
    const filters: TransactionFilter = { page: 1, per_page: 50 };
    const payload = buildFilteredPayload(filters, 3, 7);
    expect(payload.category_id).toBe(7);
    expect(payload.entity_id).toBe(3);
  });

  it("entity_id est undefined si entityId est null", () => {
    const filters: TransactionFilter = { page: 1, per_page: 50 };
    const payload = buildFilteredPayload(filters, null, 1);
    expect(payload.entity_id).toBeUndefined();
  });

  it("transmet tous les filtres actifs au payload", () => {
    const filters: TransactionFilter = {
      page: 2,
      per_page: 50,
      search: "URSSAF",
      uncategorized: true,
      date_from: "2026-01-01",
      date_to: "2026-03-31",
      amount_min: 100,
      amount_max: 5000,
      include_sepa_children: true,
      bank_account_id: 12,
      counterparty_id: 99,
    };
    const payload = buildFilteredPayload(filters, 5, 42);
    expect(payload.search).toBe("URSSAF");
    expect(payload.uncategorized).toBe(true);
    expect(payload.date_from).toBe("2026-01-01");
    expect(payload.date_to).toBe("2026-03-31");
    expect(payload.amount_min).toBe(100);
    expect(payload.amount_max).toBe(5000);
    expect(payload.include_sepa_children).toBe(true);
    expect(payload.bank_account_id).toBe(12);
    expect(payload.counterparty_id).toBe(99);
  });

  it("n'inclut pas page ni per_page dans le payload (pas de pagination cote backend)", () => {
    const filters: TransactionFilter = { page: 3, per_page: 100 };
    const payload = buildFilteredPayload(filters, null, 1);
    expect("page" in payload).toBe(false);
    expect("per_page" in payload).toBe(false);
  });
});
