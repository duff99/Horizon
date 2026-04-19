import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { CategoryCombobox } from "./CategoryCombobox";

const cats = [
  { id: 1, name: "Encaissements", slug: "encaissements", parent_category_id: null },
  { id: 2, name: "Ventes clients", slug: "ventes-clients", parent_category_id: 1 },
  { id: 3, name: "Charges sociales", slug: "charges-sociales", parent_category_id: null },
  { id: 4, name: "URSSAF", slug: "urssaf", parent_category_id: 3 },
];

describe("CategoryCombobox", () => {
  it("renders categories hierarchically", () => {
    render(<CategoryCombobox categories={cats} value={null} onChange={() => {}} />);
    expect(screen.getByRole("combobox")).toBeInTheDocument();
  });

  it("fires onChange with selected id", async () => {
    const onChange = vi.fn();
    render(<CategoryCombobox categories={cats} value={null} onChange={onChange} />);
    await userEvent.click(screen.getByRole("combobox"));
    await userEvent.click(screen.getByText("URSSAF"));
    expect(onChange).toHaveBeenCalledWith(4);
  });

  it("displays full path for selected", () => {
    render(<CategoryCombobox categories={cats} value={4} onChange={() => {}} />);
    expect(screen.getByRole("combobox")).toHaveTextContent(/Charges sociales.*URSSAF/);
  });
});
