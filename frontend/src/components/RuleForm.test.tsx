import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RuleForm } from "./RuleForm";

function Wrapped({ onSubmit }: { onSubmit: ReturnType<typeof vi.fn> }) {
  const qc = new QueryClient();
  return (
    <QueryClientProvider client={qc}>
      <RuleForm
        categories={[
          { id: 1, name: "URSSAF", slug: "urssaf", parent_category_id: null },
        ]}
        entities={[{ id: 10, name: "ACREED" }]}
        counterparties={[]}
        bankAccounts={[]}
        initialValue={null}
        onSubmit={onSubmit}
        onCancel={() => {}}
      />
    </QueryClientProvider>
  );
}

describe("RuleForm", () => {
  it("submits with minimal valid payload", async () => {
    const onSubmit = vi.fn();
    render(<Wrapped onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText(/nom/i), "Test");
    await userEvent.type(screen.getByLabelText(/priorité/i), "1234");
    await userEvent.type(screen.getByLabelText(/libellé contient/i), "URSSAF");
    // Select category via combobox (last combobox in the form is the CategoryCombobox)
    const comboboxes = screen.getAllByRole("combobox");
    await userEvent.click(comboboxes[comboboxes.length - 1]);
    await userEvent.click(screen.getByRole("option", { name: "URSSAF" }));
    await userEvent.click(screen.getByRole("button", { name: "Créer" }));
    expect(onSubmit).toHaveBeenCalled();
  });
});
