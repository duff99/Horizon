import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi } from "vitest";

import { HelpDrawer } from "./HelpDrawer";
import type { DocSectionData } from "@/content/documentation";

const section: DocSectionData = {
  id: "regles",
  title: "Règles",
  subtitle: "Subtitle",
  sees: ["S1"],
  does: ["D1"],
  tips: ["T1"],
};

function renderDrawer(props: {
  isOpen: boolean;
  onOpenChange?: (next: boolean) => void;
  section?: DocSectionData | null;
}) {
  return render(
    <MemoryRouter>
      <HelpDrawer
        section={props.section ?? section}
        isOpen={props.isOpen}
        onOpenChange={props.onOpenChange ?? (() => {})}
      />
    </MemoryRouter>,
  );
}

describe("HelpDrawer", () => {
  it("renders nothing when section is null", () => {
    const { container } = renderDrawer({ isOpen: true, section: null });
    expect(container.querySelector("[role='dialog']")).toBeNull();
  });

  it("renders the section title when open", () => {
    renderDrawer({ isOpen: true });
    expect(
      screen.getByRole("heading", { level: 2, name: "Règles" }),
    ).toBeInTheDocument();
  });

  it("does not render the dialog when closed", () => {
    renderDrawer({ isOpen: false });
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("calls onOpenChange(false) when the close button is clicked", async () => {
    const onOpenChange = vi.fn();
    renderDrawer({ isOpen: true, onOpenChange });
    await userEvent.click(
      screen.getByRole("button", { name: /Fermer l'aide/i }),
    );
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
