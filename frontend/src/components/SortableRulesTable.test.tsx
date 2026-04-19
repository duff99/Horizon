import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SortableRulesTable } from "./SortableRulesTable";
import type { Rule } from "@/api/rules";

const rules: Rule[] = [
  {
    id: 1, name: "A", entity_id: null, priority: 100, is_system: false,
    label_operator: "CONTAINS", label_value: "A", direction: "ANY",
    amount_operator: null, amount_value: null, amount_value2: null,
    counterparty_id: null, bank_account_id: null, category_id: 1,
    created_at: "", updated_at: "",
  },
  {
    id: 2, name: "B", entity_id: null, priority: 200, is_system: true,
    label_operator: "CONTAINS", label_value: "B", direction: "ANY",
    amount_operator: null, amount_value: null, amount_value2: null,
    counterparty_id: null, bank_account_id: null, category_id: 1,
    created_at: "", updated_at: "",
  },
];

describe("SortableRulesTable", () => {
  it("renders all rules with system badge", () => {
    render(
      <SortableRulesTable
        rules={rules}
        categories={[{ id: 1, name: "c", slug: "c", parent_category_id: null }]}
        onReorder={vi.fn()}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        canDelete
      />
    );
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.getByText("B")).toBeInTheDocument();
    expect(screen.getByText(/système/i)).toBeInTheDocument();
  });
});
