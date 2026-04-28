import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect } from "vitest";

import { HelpContent } from "./HelpContent";
import type { DocSectionData } from "@/content/documentation";

const baseSection: DocSectionData = {
  id: "regles",
  title: "Règles",
  subtitle: "Sous-titre complet de la section.",
  sees: ["S1", "S2"],
  does: ["D1", "D2"],
  tips: ["T1"],
};

function renderSection(section: DocSectionData) {
  return render(
    <MemoryRouter>
      <HelpContent section={section} />
    </MemoryRouter>,
  );
}

describe("HelpContent", () => {
  it("renders the title and subtitle when no panel override", () => {
    renderSection(baseSection);
    expect(
      screen.getByRole("heading", { level: 2, name: "Règles" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Sous-titre complet de la section."),
    ).toBeInTheDocument();
  });

  it("renders sees, does and tips items", () => {
    renderSection(baseSection);
    expect(screen.getByText("S1")).toBeInTheDocument();
    expect(screen.getByText("D1")).toBeInTheDocument();
    expect(screen.getByText("T1")).toBeInTheDocument();
  });

  it("uses panel.summary instead of subtitle when provided", () => {
    renderSection({
      ...baseSection,
      panel: { summary: "Résumé court pour le panneau." },
    });
    expect(
      screen.getByText("Résumé court pour le panneau."),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Sous-titre complet de la section."),
    ).toBeNull();
  });

  it("replaces sees with panel.sees override", () => {
    renderSection({
      ...baseSection,
      panel: { sees: ["alt-S1"] },
    });
    expect(screen.getByText("alt-S1")).toBeInTheDocument();
    expect(screen.queryByText("S1")).toBeNull();
  });

  it("hides a block when listed in panel.hide", () => {
    renderSection({
      ...baseSection,
      panel: { hide: ["tips"] },
    });
    expect(screen.getByText("S1")).toBeInTheDocument();
    expect(screen.queryByText("T1")).toBeNull();
  });

  it("links to the full documentation anchor for this section", () => {
    renderSection(baseSection);
    const link = screen.getByRole("link", {
      name: /Voir le guide complet/i,
    });
    expect(link.getAttribute("href")).toBe("/documentation#regles");
  });
});
