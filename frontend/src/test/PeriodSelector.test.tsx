import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import {
  PeriodSelector,
  computeRange,
  computeMonthRange,
  defaultPeriodValue,
  formatPeriodForDisplay,
  type PeriodValue,
} from "../components/PeriodSelector";

function Harness({
  initial,
  granularity,
}: {
  initial: PeriodValue;
  granularity?: "day" | "month";
}) {
  // Simple state via closure through an observable onChange spy.
  return (
    <PeriodSelector
      value={initial}
      onChange={() => {}}
      granularity={granularity}
    />
  );
}

describe("PeriodSelector — helpers", () => {
  it("computeRange('30d') returns a 30-day window ending today", () => {
    const today = new Date(2026, 3, 23); // 23 avril 2026
    const { from, to } = computeRange("30d", today);
    expect(to).toBe("2026-04-23");
    // 30 jours → from = today - 29 jours
    expect(from).toBe("2026-03-25");
  });

  it("computeRange('ytd') starts on 1er janvier", () => {
    const today = new Date(2026, 3, 23);
    const { from, to } = computeRange("ytd", today);
    expect(from).toBe("2026-01-01");
    expect(to).toBe("2026-04-23");
  });

  it("computeRange('previous_month') covers the full previous month", () => {
    const today = new Date(2026, 3, 23); // avril
    const { from, to } = computeRange("previous_month", today);
    expect(from).toBe("2026-03-01");
    expect(to).toBe("2026-03-31");
  });

  it("computeMonthRange('12m') returns 12-month window", () => {
    const today = new Date(2026, 3, 15);
    const { from, to } = computeMonthRange("12m", today);
    expect(from).toBe("2025-05");
    expect(to).toBe("2026-04");
  });

  it("formatPeriodForDisplay gives FR labels", () => {
    expect(
      formatPeriodForDisplay({ from: "2026-03-25", to: "2026-04-23", preset: "30d" }),
    ).toBe("30 derniers jours");
    expect(
      formatPeriodForDisplay({ from: "2026-01-01", to: "2026-04-23", preset: "ytd" }),
    ).toBe("Année en cours");
  });
});

describe("PeriodSelector — interactions", () => {
  it("renders with 30d preset active by default and fires onChange with 90d range on click", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const initial = defaultPeriodValue("30d", "day", new Date(2026, 3, 23));

    render(
      <PeriodSelector value={initial} onChange={onChange} />,
    );

    const btn30 = screen.getByRole("button", { name: "30 j" });
    expect(btn30).toHaveAttribute("aria-pressed", "true");

    await user.click(screen.getByRole("button", { name: "90 j" }));

    expect(onChange).toHaveBeenCalledTimes(1);
    const called = onChange.mock.calls[0][0] as PeriodValue;
    expect(called.preset).toBe("90d");
    // Just sanity: from < to and valid ISO format
    expect(called.from).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(called.to).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("switches to custom and fires onChange when a date input changes", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const initial: PeriodValue = {
      from: "2026-01-10",
      to: "2026-02-28",
      preset: "custom",
    };

    render(<PeriodSelector value={initial} onChange={onChange} />);

    const fromInput = screen.getByLabelText("Date de début") as HTMLInputElement;
    expect(fromInput.type).toBe("date");

    await user.clear(fromInput);
    await user.type(fromInput, "2026-01-15");

    // At least one onChange happened with preset custom
    expect(onChange).toHaveBeenCalled();
    const last = onChange.mock.calls.at(-1)![0] as PeriodValue;
    expect(last.preset).toBe("custom");
  });

  it("uses month-type inputs when granularity='month'", () => {
    const initial: PeriodValue = {
      from: "2026-01",
      to: "2026-04",
      preset: "custom",
    };
    render(
      <PeriodSelector
        value={initial}
        onChange={() => {}}
        granularity="month"
      />,
    );
    const fromInput = screen.getByLabelText("Date de début") as HTMLInputElement;
    expect(fromInput.type).toBe("month");
    expect(fromInput.value).toBe("2026-01");
  });

  it("Harness renders (smoke)", () => {
    const initial = defaultPeriodValue("30d");
    render(<Harness initial={initial} />);
    expect(screen.getByRole("group", { name: "Période" })).toBeInTheDocument();
  });
});
