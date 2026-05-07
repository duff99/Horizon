import { render, screen, fireEvent, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RuleForm } from "./RuleForm";
import * as rulesApi from "@/api/rules";

vi.mock("@/api/rules", async (importOriginal) => {
  const actual = await importOriginal<typeof rulesApi>();
  return {
    ...actual,
    previewRule: vi.fn().mockResolvedValue({ matching_count: 0, sample: [] }),
  };
});

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
  it("affiche les champs principaux du formulaire", () => {
    render(<Wrapped onSubmit={vi.fn()} />);
    expect(screen.getByLabelText(/nom de la règle/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/priorité/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/texte du filtre/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Créer" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aperçu" })).toBeInTheDocument();
  });

  it("affiche une erreur si on soumet sans categorie ni filtre", async () => {
    const onSubmit = vi.fn();
    render(<Wrapped onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText(/nom de la règle/i), "Test");
    await userEvent.click(screen.getByRole("button", { name: "Créer" }));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  describe("aperçu live debounced (E3)", () => {
    beforeEach(() => {
      vi.useFakeTimers();
      vi.mocked(rulesApi.previewRule).mockClear();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it("ne declenche pas previewRule avant le delai de debounce", () => {
      render(<Wrapped onSubmit={vi.fn()} />);
      const input = screen.getByLabelText(/texte du filtre/i);
      fireEvent.change(input, { target: { value: "AGICAP" } });
      expect(rulesApi.previewRule).not.toHaveBeenCalled();
    });

    it("declenche previewRule automatiquement apres le debounce", async () => {
      render(<Wrapped onSubmit={vi.fn()} />);
      const input = screen.getByLabelText(/texte du filtre/i);
      fireEvent.change(input, { target: { value: "AGICAP" } });
      expect(rulesApi.previewRule).not.toHaveBeenCalled();
      await act(async () => {
        vi.runAllTimers();
      });
      expect(rulesApi.previewRule).toHaveBeenCalledTimes(1);
    });

    it("ne declenche pas previewRule quand aucun filtre n'est saisi", async () => {
      render(<Wrapped onSubmit={vi.fn()} />);
      await act(async () => {
        vi.runAllTimers();
      });
      expect(rulesApi.previewRule).not.toHaveBeenCalled();
    });
  });
});
