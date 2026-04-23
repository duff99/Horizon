import { render, screen, fireEvent, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect } from "vitest";

import { DocumentationPage } from "../pages/DocumentationPage";
import { DOC_SECTIONS } from "../content/documentation";

function renderPage() {
  return render(
    <MemoryRouter>
      <DocumentationPage />
    </MemoryRouter>,
  );
}

describe("DocumentationPage", () => {
  it("renders the page header", () => {
    renderPage();
    expect(
      screen.getByRole("heading", { level: 1, name: /Documentation Horizon/i }),
    ).toBeInTheDocument();
  });

  it("renders at least 11 sections in the TOC with matching anchors", () => {
    const { container } = renderPage();

    expect(DOC_SECTIONS.length).toBeGreaterThanOrEqual(11);

    // TOC rendered in a <nav aria-label="Table des matières">.
    const toc = screen.getByRole("navigation", {
      name: /Table des matières/i,
    });
    const links = within(toc).getAllByRole("link");
    expect(links.length).toBe(DOC_SECTIONS.length);

    // Each section must have an element with its id as anchor target.
    for (const s of DOC_SECTIONS) {
      const anchor = container.querySelector(`#${s.id}`);
      expect(anchor).not.toBeNull();
    }

    // Each section title should appear at heading level 2.
    for (const s of DOC_SECTIONS) {
      expect(
        screen.getByRole("heading", { level: 2, name: s.title }),
      ).toBeInTheDocument();
    }
  });

  it("TOC links point to section anchors", () => {
    renderPage();
    const toc = screen.getByRole("navigation", {
      name: /Table des matières/i,
    });
    const firstLink = within(toc).getAllByRole("link")[0];
    expect(firstLink.getAttribute("href")).toBe(`#${DOC_SECTIONS[0].id}`);
  });

  it("filters sections by free-text search", () => {
    renderPage();
    const search = screen.getByRole("searchbox", {
      name: /Rechercher dans la documentation/i,
    });

    // Keyword only present in the "Prévisionnel" section description.
    fireEvent.change(search, { target: { value: "Agicap" } });

    expect(
      screen.getByRole("heading", { level: 2, name: /Prévisionnel/i }),
    ).toBeInTheDocument();
    // A non-matching section must disappear after filter.
    expect(
      screen.queryByRole("heading", { level: 2, name: /^Profil$/i }),
    ).toBeNull();
  });

  it("shows an empty state when the search matches nothing", () => {
    renderPage();
    const search = screen.getByRole("searchbox", {
      name: /Rechercher dans la documentation/i,
    });
    fireEvent.change(search, { target: { value: "zzzzzzzzz-unknown" } });
    expect(screen.getByText(/Aucune section/i)).toBeInTheDocument();
  });
});
