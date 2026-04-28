import { describe, it, expect } from "vitest";

import { resolveHelpSection } from "./help-routes";

describe("resolveHelpSection", () => {
  it("returns the rules section for /regles", () => {
    const section = resolveHelpSection("/regles");
    expect(section?.id).toBe("regles");
  });

  it("returns the imports section for both /imports and /imports/nouveau", () => {
    expect(resolveHelpSection("/imports")?.id).toBe("imports");
    expect(resolveHelpSection("/imports/nouveau")?.id).toBe("imports");
  });

  it("matches /administration/audit before /administration", () => {
    // The audit page has its own dedicated doc section.
    expect(resolveHelpSection("/administration/audit")?.id).toBe("audit");
  });

  it("returns the administration section for other admin sub-routes", () => {
    expect(resolveHelpSection("/administration/utilisateurs")?.id).toBe(
      "administration",
    );
    expect(resolveHelpSection("/administration/societes")?.id).toBe(
      "administration",
    );
    expect(resolveHelpSection("/administration/comptes-bancaires")?.id).toBe(
      "administration",
    );
  });

  it("returns null for routes without help (login, documentation)", () => {
    expect(resolveHelpSection("/connexion")).toBeNull();
    expect(resolveHelpSection("/documentation")).toBeNull();
  });

  it("returns null for unknown routes", () => {
    expect(resolveHelpSection("/qsdkjfh")).toBeNull();
    expect(resolveHelpSection("/")).toBeNull();
  });

  it("returns sections that match top-level metier routes", () => {
    expect(resolveHelpSection("/tableau-de-bord")?.id).toBe("tableau-de-bord");
    expect(resolveHelpSection("/analyse")?.id).toBe("analyse");
    expect(resolveHelpSection("/previsionnel")?.id).toBe("previsionnel");
    expect(resolveHelpSection("/transactions")?.id).toBe("transactions");
    expect(resolveHelpSection("/engagements")?.id).toBe("engagements");
    expect(resolveHelpSection("/tiers")?.id).toBe("tiers");
    expect(resolveHelpSection("/profil")?.id).toBe("profil");
  });
});
