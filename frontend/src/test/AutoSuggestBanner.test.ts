/**
 * Tests E4 — auto-suggestion de regle apres categorisations manuelles repetees.
 *
 * On teste la logique de filtrage des suggestions (dismissed) de facon isolee.
 * Le rendu complet de TransactionsPage ne peut pas etre teste dans jsdom
 * (echec Radix Select pre-existant).
 */
import { describe, it, expect } from "vitest";
import type { AutoSuggestItem } from "../api/rules";

/**
 * Reproduit la logique de filtrage des suggestions dans TransactionsPage.tsx.
 */
function filterVisibleSuggestions(
  suggestions: AutoSuggestItem[],
  dismissed: Set<string>,
): AutoSuggestItem[] {
  return suggestions.filter((s) => !dismissed.has(s.normalized_label));
}

const mockSuggestions: AutoSuggestItem[] = [
  { normalized_label: "PRLV AGICAP", category_id: 1, category_name: "SaaS", manual_count: 4 },
  { normalized_label: "VIR SALAIRES", category_id: 2, category_name: "Remunérations", manual_count: 3 },
  { normalized_label: "CB AMAZON", category_id: 3, category_name: "Achats", manual_count: 5 },
];

describe("E4 — filterVisibleSuggestions", () => {
  it("retourne toutes les suggestions quand aucune n'est dismissée", () => {
    const visible = filterVisibleSuggestions(mockSuggestions, new Set());
    expect(visible).toHaveLength(3);
  });

  it("exclut les suggestions dont le label est dans dismissed", () => {
    const dismissed = new Set(["PRLV AGICAP"]);
    const visible = filterVisibleSuggestions(mockSuggestions, dismissed);
    expect(visible).toHaveLength(2);
    expect(visible.map((s) => s.normalized_label)).not.toContain("PRLV AGICAP");
  });

  it("retourne une liste vide si toutes les suggestions sont dismissées", () => {
    const dismissed = new Set(mockSuggestions.map((s) => s.normalized_label));
    const visible = filterVisibleSuggestions(mockSuggestions, dismissed);
    expect(visible).toHaveLength(0);
  });

  it("retourne une liste vide si suggestions est vide", () => {
    const visible = filterVisibleSuggestions([], new Set());
    expect(visible).toHaveLength(0);
  });

  it("le dismiss est sensible à la casse (exacte correspondance de clé)", () => {
    // Le label normalise est en majuscules cote backend ; la clé de dismiss doit matcher exactement.
    const dismissed = new Set(["prlv agicap"]); // minuscules — ne doit pas matcher
    const visible = filterVisibleSuggestions(mockSuggestions, dismissed);
    expect(visible).toHaveLength(3); // PRLV AGICAP (majuscules) reste visible
  });
});
