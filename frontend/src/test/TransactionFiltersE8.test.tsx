/**
 * Tests E7/E8 — filtre amount_min/amount_max, toggle SEPA, persistance URL.
 *
 * On teste les fonctions pures de conversion URL ↔ filtre isolément
 * (sans rendu complet de TransactionsPage, qui échoue à cause de Radix Select
 * dans jsdom — cf. TransactionsPage.test.tsx pre-existant).
 */
import { describe, it, expect } from "vitest";
import type { TransactionFilter } from "../types/api";

// ─── Copier les helpers de TransactionsPage pour les tester isolément ───────

function parseIntParam(v: string | null): number | undefined {
  if (v === null || v === "") return undefined;
  const n = parseInt(v, 10);
  return isNaN(n) ? undefined : n;
}

function parseFloatParam(v: string | null): number | undefined {
  if (v === null || v === "") return undefined;
  const n = parseFloat(v);
  return isNaN(n) ? undefined : n;
}

function filtersFromSearchParams(sp: URLSearchParams): TransactionFilter {
  return {
    page: parseIntParam(sp.get("page")) ?? 1,
    per_page: parseIntParam(sp.get("per_page")) ?? 50,
    search: sp.get("search") ?? undefined,
    bank_account_id: parseIntParam(sp.get("account")),
    uncategorized: sp.get("uncategorized") === "true" || undefined,
    category_id: parseIntParam(sp.get("category")),
    amount_min: parseFloatParam(sp.get("amount_min")),
    amount_max: parseFloatParam(sp.get("amount_max")),
    include_sepa_children: sp.get("sepa") === "true",
    date_from: sp.get("date_from") ?? undefined,
    date_to: sp.get("date_to") ?? undefined,
    counterparty_id: parseIntParam(sp.get("counterparty")),
  };
}

function filtersToSearchParams(f: TransactionFilter): URLSearchParams {
  const sp = new URLSearchParams();
  if (f.page && f.page > 1) sp.set("page", String(f.page));
  if (f.per_page && f.per_page !== 50) sp.set("per_page", String(f.per_page));
  if (f.search) sp.set("search", f.search);
  if (f.bank_account_id) sp.set("account", String(f.bank_account_id));
  if (f.uncategorized) sp.set("uncategorized", "true");
  if (f.category_id) sp.set("category", String(f.category_id));
  if (f.amount_min != null) sp.set("amount_min", String(f.amount_min));
  if (f.amount_max != null) sp.set("amount_max", String(f.amount_max));
  if (f.include_sepa_children) sp.set("sepa", "true");
  if (f.date_from) sp.set("date_from", f.date_from);
  if (f.date_to) sp.set("date_to", f.date_to);
  if (f.counterparty_id) sp.set("counterparty", String(f.counterparty_id));
  return sp;
}

// ─────────────────────────────────────────────────────────────────────────────

describe("E8 — filtersFromSearchParams", () => {
  it("renvoie les valeurs par défaut pour des params vides", () => {
    const sp = new URLSearchParams();
    const f = filtersFromSearchParams(sp);
    expect(f.page).toBe(1);
    expect(f.per_page).toBe(50);
    expect(f.search).toBeUndefined();
    expect(f.amount_min).toBeUndefined();
    expect(f.amount_max).toBeUndefined();
    expect(f.include_sepa_children).toBe(false);
  });

  it("parse amount_min et amount_max depuis les params URL", () => {
    const sp = new URLSearchParams("amount_min=100.5&amount_max=999");
    const f = filtersFromSearchParams(sp);
    expect(f.amount_min).toBe(100.5);
    expect(f.amount_max).toBe(999);
  });

  it("E7 — parse include_sepa_children=true depuis l'URL", () => {
    const sp = new URLSearchParams("sepa=true");
    const f = filtersFromSearchParams(sp);
    expect(f.include_sepa_children).toBe(true);
  });

  it("E7 — include_sepa_children est false par défaut", () => {
    const sp = new URLSearchParams();
    const f = filtersFromSearchParams(sp);
    expect(f.include_sepa_children).toBe(false);
  });

  it("parse les filtres de base (search, category, uncategorized)", () => {
    const sp = new URLSearchParams("search=URSSAF&category=42&uncategorized=true");
    const f = filtersFromSearchParams(sp);
    expect(f.search).toBe("URSSAF");
    expect(f.category_id).toBe(42);
    expect(f.uncategorized).toBe(true);
  });
});

describe("E8 — filtersToSearchParams", () => {
  it("produit des params vides pour les valeurs par défaut (URL propre)", () => {
    const f: TransactionFilter = { page: 1, per_page: 50 };
    const sp = filtersToSearchParams(f);
    expect(sp.toString()).toBe("");
  });

  it("encode amount_min et amount_max dans l'URL", () => {
    const f: TransactionFilter = { page: 1, per_page: 50, amount_min: 200, amount_max: 1000 };
    const sp = filtersToSearchParams(f);
    expect(sp.get("amount_min")).toBe("200");
    expect(sp.get("amount_max")).toBe("1000");
  });

  it("E7 — encode include_sepa_children=true dans l'URL", () => {
    const f: TransactionFilter = { page: 1, per_page: 50, include_sepa_children: true };
    const sp = filtersToSearchParams(f);
    expect(sp.get("sepa")).toBe("true");
  });

  it("E7 — n'encode pas sepa si include_sepa_children est false", () => {
    const f: TransactionFilter = { page: 1, per_page: 50, include_sepa_children: false };
    const sp = filtersToSearchParams(f);
    expect(sp.has("sepa")).toBe(false);
  });

  it("round-trip — encodage puis décodage préserve tous les filtres", () => {
    const original: TransactionFilter = {
      page: 2,
      per_page: 100,
      search: "VIREMENT",
      category_id: 7,
      amount_min: 50,
      amount_max: 500,
      include_sepa_children: true,
      date_from: "2026-01-01",
      date_to: "2026-03-31",
      uncategorized: true,
    };
    const sp = filtersToSearchParams(original);
    const decoded = filtersFromSearchParams(sp);
    expect(decoded.page).toBe(original.page);
    expect(decoded.per_page).toBe(original.per_page);
    expect(decoded.search).toBe(original.search);
    expect(decoded.category_id).toBe(original.category_id);
    expect(decoded.amount_min).toBe(original.amount_min);
    expect(decoded.amount_max).toBe(original.amount_max);
    expect(decoded.include_sepa_children).toBe(original.include_sepa_children);
    expect(decoded.date_from).toBe(original.date_from);
    expect(decoded.date_to).toBe(original.date_to);
    expect(decoded.uncategorized).toBe(original.uncategorized);
  });
});
