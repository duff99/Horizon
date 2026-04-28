import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";

import { HelpProvider, useHelp } from "./HelpProvider";

function Probe() {
  const { isOpen, open, close, toggle } = useHelp();
  return (
    <div>
      <span data-testid="state">{isOpen ? "open" : "closed"}</span>
      <button onClick={open}>open</button>
      <button onClick={close}>close</button>
      <button onClick={toggle}>toggle</button>
    </div>
  );
}

function renderProbe() {
  return render(
    <HelpProvider>
      <Probe />
    </HelpProvider>,
  );
}

describe("HelpProvider", () => {
  it("starts closed", () => {
    renderProbe();
    expect(screen.getByTestId("state")).toHaveTextContent("closed");
  });

  it("open() and close() toggle the state", async () => {
    renderProbe();
    await userEvent.click(screen.getByText("open"));
    expect(screen.getByTestId("state")).toHaveTextContent("open");
    await userEvent.click(screen.getByText("close"));
    expect(screen.getByTestId("state")).toHaveTextContent("closed");
  });

  it("toggle() flips the state", async () => {
    renderProbe();
    await userEvent.click(screen.getByText("toggle"));
    expect(screen.getByTestId("state")).toHaveTextContent("open");
    await userEvent.click(screen.getByText("toggle"));
    expect(screen.getByTestId("state")).toHaveTextContent("closed");
  });

  it("throws when useHelp is called outside provider", () => {
    function Lone() {
      useHelp();
      return null;
    }
    // Suppress console.error noise from the expected throw.
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<Lone />)).toThrow(/useHelp must be used within/);
    spy.mockRestore();
  });
});
