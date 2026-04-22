import { describe, expect, it, beforeEach } from "vitest";
import { useEntityFilter } from "@/stores/entityFilter";

describe("useEntityFilter", () => {
  beforeEach(() => {
    localStorage.clear();
    useEntityFilter.setState({ entityId: null });
  });

  it("defaults to null", () => {
    expect(useEntityFilter.getState().entityId).toBeNull();
  });

  it("setEntityId updates the store", () => {
    useEntityFilter.getState().setEntityId(42);
    expect(useEntityFilter.getState().entityId).toBe(42);
  });

  it("persists to localStorage under horizon:entityFilter", () => {
    useEntityFilter.getState().setEntityId(7);
    const raw = localStorage.getItem("horizon:entityFilter");
    expect(raw).toContain('"entityId":7');
  });
});
