# Aide contextuelle in-page — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter un panneau d'aide latéral droit, déclenché par un bouton "Aide" injecté en haut à droite par `Layout`, qui affiche la section de `documentation.ts` correspondant à la route courante — sans quitter la page.

**Architecture:** Source unique = `src/content/documentation.ts` (étendu d'un champ optionnel `panel` pour overrides courts). Mapping route → section dans `src/lib/help-routes.ts`. Composants dans `src/components/help/` : `HelpProvider` (contexte open/close), `HelpButton` (déclencheur route-aware), `HelpDrawer` (Vaul `direction="right"`, ~420px), `HelpContent` (rendu d'une section avec overrides). `Layout` enveloppe l'app dans le provider et place le bouton.

**Tech Stack:** React 18, TypeScript 5, Vaul 1.1 (`direction="right"`), Vitest 2 + Testing Library 16 + jsdom, Tailwind 3 (tokens existants : `ink`, `ink-2`, `panel`, `panel-2`, `accent`, `line-soft`, `muted-foreground`), lucide-react (`HelpCircle`, `X`).

**Spec source:** `docs/superpowers/specs/2026-04-28-help-contextuel-design.md` (commit 657199d)

---

## File Structure

### À créer

| Fichier | Responsabilité |
|---|---|
| `frontend/src/lib/help-routes.ts` | Mapping pur route → DocSectionData. Aucune dépendance React. |
| `frontend/src/lib/help-routes.test.ts` | Tests unitaires du résolveur (pur, rapide). |
| `frontend/src/components/help/HelpProvider.tsx` | Contexte React + hook `useHelp()` (open, close, toggle, isOpen). |
| `frontend/src/components/help/HelpProvider.test.tsx` | Tests du provider et du hook. |
| `frontend/src/components/help/HelpContent.tsx` | Composant présentation : titre, summary, blocs sees/does/tips. Applique l'override `panel`. Pas de logique de drawer. |
| `frontend/src/components/help/HelpContent.test.tsx` | Tests du rendu et des overrides. |
| `frontend/src/components/help/HelpDrawer.tsx` | Wrapper Vaul `direction="right"`, ~420px, gère le rendu HelpContent + bouton fermer + lien "Voir le guide complet". |
| `frontend/src/components/help/HelpDrawer.test.tsx` | Tests du drawer. |
| `frontend/src/components/help/HelpButton.tsx` | Bouton "Aide" route-aware (lit `useLocation`, masqué sur `/connexion` et `/documentation`). Ouvre le drawer. Écoute `?` (hors input) — uniquement quand le bouton est rendu, pour éviter d'ouvrir un drawer invisible sur les pages sans aide. |
| `frontend/src/components/help/HelpButton.test.tsx` | Tests de la visibilité et du clic. |

### À modifier

| Fichier | Modification |
|---|---|
| `frontend/src/content/documentation.ts` | Ajouter le champ optionnel `panel?` au type `DocSectionData`. Aucun changement de données. |
| `frontend/src/components/Layout.tsx` | Envelopper l'app dans `<HelpProvider>` ; placer `<HelpButton>` en `fixed top-6 right-6 z-40`. |
| `README.md` (racine) | Ajouter section "Discipline éditoriale" rappelant que toute modif d'une page doit refléter dans `src/content/documentation.ts`. |

### Tests setup existant (à connaître)

- `frontend/src/test/setup.ts` mocke déjà `ResizeObserver` et `scrollIntoView` — Vaul s'appuie sur `ResizeObserver`, donc rien à ajouter.
- `frontend/vite.config.ts` configure Vitest : `globals: true`, `environment: "jsdom"`, `setupFiles: ["./src/test/setup.ts"]`.
- Lancement : `cd frontend && npm test` (vitest --run, tous les tests). Pour un fichier : `npm test -- src/lib/help-routes.test.ts`.

---

## Task 1: Étendre `DocSectionData` avec le champ optionnel `panel`

**Files:**
- Modify: `frontend/src/content/documentation.ts:13-20`

C'est une extension de type strictement additive — aucune section existante ne change, tous les tests existants doivent continuer à passer.

- [ ] **Step 1.1: Modifier l'interface**

Remplacer dans `frontend/src/content/documentation.ts` lignes 13-20 :

```ts
export interface DocSectionData {
  id: string;
  title: string;
  subtitle: string;
  sees: string[];
  does: string[];
  tips?: string[];
  /**
   * Override optionnel pour le panneau d'aide contextuel.
   * Si absent, le panneau réutilise subtitle / sees / does / tips.
   * Si présent : `summary` remplace subtitle, et `sees/does/tips` (s'ils sont
   * définis) remplacent leurs équivalents. `hide` permet de masquer un bloc
   * entier dans le panneau sans le retirer de la doc complète.
   */
  panel?: {
    summary?: string;
    sees?: string[];
    does?: string[];
    tips?: string[];
    hide?: ("sees" | "does" | "tips")[];
  };
}
```

- [ ] **Step 1.2: Vérifier que tout compile**

Run: `cd frontend && npx tsc -b --noEmit`
Expected: aucune erreur (l'extension est strictement additive).

- [ ] **Step 1.3: Lancer la suite de tests existante pour vérifier qu'aucune régression n'a été introduite**

Run: `cd frontend && npm test -- src/test/DocumentationPage.test.tsx`
Expected: PASS (5 tests).

- [ ] **Step 1.4: Commit**

```bash
git add frontend/src/content/documentation.ts
git commit -m "feat(help): extend DocSectionData with optional panel override field"
```

---

## Task 2: Module `help-routes` — résolveur pur

**Files:**
- Create: `frontend/src/lib/help-routes.ts`
- Test: `frontend/src/lib/help-routes.test.ts`

Module pur, sans dépendance React. Mapping ordonné des routes vers les sections.

- [ ] **Step 2.1: Écrire le test (failing)**

Créer `frontend/src/lib/help-routes.test.ts` :

```ts
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
```

- [ ] **Step 2.2: Run tests — verify they fail**

Run: `cd frontend && npm test -- src/lib/help-routes.test.ts`
Expected: FAIL with `Cannot find module './help-routes'`.

- [ ] **Step 2.3: Write the minimal implementation**

Créer `frontend/src/lib/help-routes.ts` :

```ts
import { DOC_SECTIONS, type DocSectionData } from "@/content/documentation";

/**
 * Mapping route → sectionId. L'ordre est significatif : le premier match gagne.
 * `/administration/audit` doit précéder `/administration` car c'est plus spécifique.
 */
const HELP_ROUTES: { match: RegExp; sectionId: string }[] = [
  { match: /^\/tableau-de-bord/, sectionId: "tableau-de-bord" },
  { match: /^\/analyse/, sectionId: "analyse" },
  { match: /^\/previsionnel/, sectionId: "previsionnel" },
  { match: /^\/transactions/, sectionId: "transactions" },
  { match: /^\/imports/, sectionId: "imports" },
  { match: /^\/engagements/, sectionId: "engagements" },
  { match: /^\/tiers/, sectionId: "tiers" },
  { match: /^\/regles/, sectionId: "regles" },
  { match: /^\/profil/, sectionId: "profil" },
  { match: /^\/administration\/audit/, sectionId: "audit" },
  { match: /^\/administration/, sectionId: "administration" },
];

/**
 * Renvoie la section d'aide à afficher pour une route, ou `null` si la route
 * n'a pas d'aide associée (page de connexion, page documentation, route inconnue).
 */
export function resolveHelpSection(pathname: string): DocSectionData | null {
  const hit = HELP_ROUTES.find((r) => r.match.test(pathname));
  if (!hit) return null;
  return DOC_SECTIONS.find((s) => s.id === hit.sectionId) ?? null;
}
```

- [ ] **Step 2.4: Run tests — verify they pass**

Run: `cd frontend && npm test -- src/lib/help-routes.test.ts`
Expected: PASS (7 tests).

- [ ] **Step 2.5: Commit**

```bash
git add frontend/src/lib/help-routes.ts frontend/src/lib/help-routes.test.ts
git commit -m "feat(help): route-to-section resolver"
```

---

## Task 3: `HelpProvider` — contexte React

**Files:**
- Create: `frontend/src/components/help/HelpProvider.tsx`
- Test: `frontend/src/components/help/HelpProvider.test.tsx`

Provider qui expose `isOpen`, `open()`, `close()`, `toggle()`. Le raccourci `?` est attaché plus tard dans `HelpButton` (Task 6), pas ici — on évite ainsi qu'il s'arme sur les pages sans aide.

- [ ] **Step 3.1: Écrire le test (failing)**

Créer `frontend/src/components/help/HelpProvider.test.tsx` :

```tsx
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
```

- [ ] **Step 3.2: Run test — verify it fails**

Run: `cd frontend && npm test -- src/components/help/HelpProvider.test.tsx`
Expected: FAIL with `Cannot find module './HelpProvider'`.

- [ ] **Step 3.3: Write the minimal implementation**

Créer `frontend/src/components/help/HelpProvider.tsx` :

```tsx
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

interface HelpContextValue {
  isOpen: boolean;
  open: () => void;
  close: () => void;
  toggle: () => void;
}

const HelpContext = createContext<HelpContextValue | null>(null);

export function HelpProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => setIsOpen((prev) => !prev), []);

  const value = useMemo(
    () => ({ isOpen, open, close, toggle }),
    [isOpen, open, close, toggle],
  );

  return <HelpContext.Provider value={value}>{children}</HelpContext.Provider>;
}

export function useHelp(): HelpContextValue {
  const ctx = useContext(HelpContext);
  if (!ctx) {
    throw new Error("useHelp must be used within a <HelpProvider>");
  }
  return ctx;
}
```

- [ ] **Step 3.4: Run tests — verify they pass**

Run: `cd frontend && npm test -- src/components/help/HelpProvider.test.tsx`
Expected: PASS (4 tests).

- [ ] **Step 3.5: Commit**

```bash
git add frontend/src/components/help/HelpProvider.tsx frontend/src/components/help/HelpProvider.test.tsx
git commit -m "feat(help): HelpProvider context with ? keyboard shortcut"
```

---

## Task 4: `HelpContent` — rendu présentation d'une section

**Files:**
- Create: `frontend/src/components/help/HelpContent.tsx`
- Test: `frontend/src/components/help/HelpContent.test.tsx`

Composant pur de présentation. Reçoit une `DocSectionData`, applique les overrides du champ `panel` si présent. Rend titre, summary, blocs sees/does/tips et un lien "Voir le guide complet".

- [ ] **Step 4.1: Écrire le test (failing)**

Créer `frontend/src/components/help/HelpContent.test.tsx` :

```tsx
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
```

- [ ] **Step 4.2: Run test — verify it fails**

Run: `cd frontend && npm test -- src/components/help/HelpContent.test.tsx`
Expected: FAIL with `Cannot find module './HelpContent'`.

- [ ] **Step 4.3: Write the minimal implementation**

Créer `frontend/src/components/help/HelpContent.tsx` :

```tsx
import { Link } from "react-router-dom";

import type { DocSectionData } from "@/content/documentation";

type Block = "sees" | "does" | "tips";

const BLOCK_LABELS: Record<Block, string> = {
  sees: "Ce que vous voyez",
  does: "Ce que vous pouvez faire",
  tips: "Astuces",
};

function resolveBlock(section: DocSectionData, kind: Block): string[] {
  const override = section.panel?.[kind];
  if (override !== undefined) return override;
  if (kind === "tips") return section.tips ?? [];
  return section[kind];
}

function isHidden(section: DocSectionData, kind: Block): boolean {
  return section.panel?.hide?.includes(kind) ?? false;
}

export function HelpContent({ section }: { section: DocSectionData }) {
  const summary = section.panel?.summary ?? section.subtitle;

  return (
    <div className="flex h-full flex-col">
      <header className="border-b border-line-soft px-6 pb-5 pt-6">
        <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-accent">
          Aide sur cette page
        </div>
        <h2 className="mt-2 text-[20px] font-semibold tracking-tight text-ink">
          {section.title}
        </h2>
        <p className="mt-2 text-[13.5px] leading-relaxed text-muted-foreground">
          {summary}
        </p>
      </header>

      <div className="flex-1 overflow-y-auto px-6 py-5">
        {(["sees", "does", "tips"] as const).map((kind) => {
          if (isHidden(section, kind)) return null;
          const items = resolveBlock(section, kind);
          if (items.length === 0) return null;
          return (
            <Block
              key={kind}
              label={BLOCK_LABELS[kind]}
              items={items}
              accent={kind === "does"}
              tone={kind === "tips" ? "muted" : "default"}
            />
          );
        })}
      </div>

      <footer className="border-t border-line-soft px-6 py-4">
        <Link
          to={`/documentation#${section.id}`}
          className="text-[13px] font-medium text-accent hover:underline"
        >
          Voir le guide complet →
        </Link>
      </footer>
    </div>
  );
}

function Block({
  label,
  items,
  accent = false,
  tone = "default",
}: {
  label: string;
  items: string[];
  accent?: boolean;
  tone?: "default" | "muted";
}) {
  return (
    <section className="mt-5 first:mt-0">
      <div className="flex items-center gap-2">
        <span
          aria-hidden
          className={
            "inline-block h-1.5 w-1.5 rounded-full " +
            (accent ? "bg-accent" : tone === "muted" ? "bg-amber-500" : "bg-ink")
          }
        />
        <h3 className="text-[10.5px] font-semibold uppercase tracking-[0.14em] text-ink-2">
          {label}
        </h3>
      </div>
      <ul className="mt-2.5 space-y-2">
        {items.map((item, idx) => (
          <li
            key={idx}
            className={
              "relative pl-4 text-[13px] leading-relaxed " +
              (tone === "muted" ? "text-ink-2" : "text-ink")
            }
          >
            <span
              aria-hidden
              className="absolute left-0 top-[0.65em] h-px w-2.5 bg-line"
            />
            {item}
          </li>
        ))}
      </ul>
    </section>
  );
}
```

- [ ] **Step 4.4: Run tests — verify they pass**

Run: `cd frontend && npm test -- src/components/help/HelpContent.test.tsx`
Expected: PASS (6 tests).

- [ ] **Step 4.5: Commit**

```bash
git add frontend/src/components/help/HelpContent.tsx frontend/src/components/help/HelpContent.test.tsx
git commit -m "feat(help): HelpContent renderer with panel overrides"
```

---

## Task 5: `HelpDrawer` — wrapper Vaul `direction="right"`

**Files:**
- Create: `frontend/src/components/help/HelpDrawer.tsx`
- Test: `frontend/src/components/help/HelpDrawer.test.tsx`

Wrapper de bas niveau autour de `vaul` avec `direction="right"`. On n'utilise PAS le composant `Drawer` existant (qui est figé en bottom-sheet) — on appelle `DrawerPrimitive` directement avec le bon styling. Largeur 420px sur desktop, full-width sous 640px.

Le drawer reçoit `section: DocSectionData | null` et `isOpen / onOpenChange`. Si `section` est null, il ne rend rien (sécurité).

- [ ] **Step 5.1: Écrire le test (failing)**

Créer `frontend/src/components/help/HelpDrawer.test.tsx` :

```tsx
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
```

- [ ] **Step 5.2: Run test — verify it fails**

Run: `cd frontend && npm test -- src/components/help/HelpDrawer.test.tsx`
Expected: FAIL with `Cannot find module './HelpDrawer'`.

- [ ] **Step 5.3: Write the minimal implementation**

Créer `frontend/src/components/help/HelpDrawer.tsx` :

```tsx
import { X } from "lucide-react";
import { Drawer as DrawerPrimitive } from "vaul";

import type { DocSectionData } from "@/content/documentation";
import { cn } from "@/lib/utils";

import { HelpContent } from "./HelpContent";

interface HelpDrawerProps {
  section: DocSectionData | null;
  isOpen: boolean;
  onOpenChange: (next: boolean) => void;
}

/**
 * Panneau d'aide latéral droit.
 *
 * - Glissé depuis la droite via Vaul `direction="right"`.
 * - 420px sur desktop, full-width sous 640px.
 * - `shouldScaleBackground={false}` car le scaling iOS de Vaul est conçu pour
 *   les bottom sheets, pas pour un panneau latéral.
 */
export function HelpDrawer({ section, isOpen, onOpenChange }: HelpDrawerProps) {
  if (!section) return null;

  return (
    <DrawerPrimitive.Root
      open={isOpen}
      onOpenChange={onOpenChange}
      direction="right"
      shouldScaleBackground={false}
    >
      <DrawerPrimitive.Portal>
        <DrawerPrimitive.Overlay
          className={cn("fixed inset-0 z-50 bg-black/50")}
        />
        <DrawerPrimitive.Content
          aria-describedby={undefined}
          className={cn(
            "fixed inset-y-0 right-0 z-50 flex h-full w-full max-w-[420px] flex-col bg-panel shadow-xl outline-none",
            "border-l border-line-soft",
          )}
        >
          <DrawerPrimitive.Title className="sr-only">
            Aide — {section.title}
          </DrawerPrimitive.Title>
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            aria-label="Fermer l'aide"
            className={cn(
              "absolute right-3 top-3 rounded-md p-1.5 text-ink-2 transition-colors",
              "hover:bg-panel-2 hover:text-ink",
            )}
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
          <HelpContent section={section} />
        </DrawerPrimitive.Content>
      </DrawerPrimitive.Portal>
    </DrawerPrimitive.Root>
  );
}
```

- [ ] **Step 5.4: Run tests — verify they pass**

Run: `cd frontend && npm test -- src/components/help/HelpDrawer.test.tsx`
Expected: PASS (4 tests).

- [ ] **Step 5.5: Commit**

```bash
git add frontend/src/components/help/HelpDrawer.tsx frontend/src/components/help/HelpDrawer.test.tsx
git commit -m "feat(help): HelpDrawer right-side panel using vaul direction=right"
```

---

## Task 6: `HelpButton` — bouton route-aware injecté par Layout

**Files:**
- Create: `frontend/src/components/help/HelpButton.tsx`
- Test: `frontend/src/components/help/HelpButton.test.tsx`

Bouton fixe top-right qui :
- lit la route via `useLocation`,
- résout la section via `resolveHelpSection`,
- ne se rend pas si la section est null,
- au clic : `useHelp().toggle()`,
- écoute `?` au clavier (uniquement quand le bouton est rendu, hors champs de saisie),
- rend le `HelpDrawer` juxtaposé.

- [ ] **Step 6.1: Écrire le test (failing)**

Créer `frontend/src/components/help/HelpButton.test.tsx` :

```tsx
import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect } from "vitest";

import { HelpButton } from "./HelpButton";
import { HelpProvider } from "./HelpProvider";

function renderAt(pathname: string) {
  return render(
    <MemoryRouter initialEntries={[pathname]}>
      <HelpProvider>
        <HelpButton />
        <input aria-label="external-input" />
      </HelpProvider>
    </MemoryRouter>,
  );
}

describe("HelpButton", () => {
  it("is not rendered on /connexion", () => {
    renderAt("/connexion");
    expect(screen.queryByRole("button", { name: /Aide/i })).toBeNull();
  });

  it("is not rendered on /documentation", () => {
    renderAt("/documentation");
    expect(screen.queryByRole("button", { name: /Aide/i })).toBeNull();
  });

  it("is rendered on /regles with aria-expanded=false initially", () => {
    renderAt("/regles");
    const btn = screen.getByRole("button", { name: /Aide/i });
    expect(btn).toBeInTheDocument();
    expect(btn).toHaveAttribute("aria-expanded", "false");
  });

  it("opens the drawer and shows the rules section when clicked", async () => {
    renderAt("/regles");
    const btn = screen.getByRole("button", { name: /Aide/i });
    await userEvent.click(btn);
    expect(btn).toHaveAttribute("aria-expanded", "true");
    expect(
      screen.getByRole("heading", { level: 2, name: /Règles/i }),
    ).toBeInTheDocument();
  });

  it("does not render on an unknown route", () => {
    renderAt("/qsdkjfh");
    expect(screen.queryByRole("button", { name: /Aide/i })).toBeNull();
  });

  it("opens on '?' key when focus is on body", () => {
    renderAt("/regles");
    const btn = screen.getByRole("button", { name: /Aide/i });
    expect(btn).toHaveAttribute("aria-expanded", "false");
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "?" }));
    });
    expect(btn).toHaveAttribute("aria-expanded", "true");
  });

  it("ignores '?' key when focus is in an input", async () => {
    renderAt("/regles");
    const btn = screen.getByRole("button", { name: /Aide/i });
    screen.getByLabelText("external-input").focus();
    await userEvent.keyboard("?");
    expect(btn).toHaveAttribute("aria-expanded", "false");
  });
});
```

- [ ] **Step 6.2: Run test — verify it fails**

Run: `cd frontend && npm test -- src/components/help/HelpButton.test.tsx`
Expected: FAIL with `Cannot find module './HelpButton'`.

- [ ] **Step 6.3: Write the minimal implementation**

Créer `frontend/src/components/help/HelpButton.tsx` :

```tsx
import { HelpCircle } from "lucide-react";
import { useEffect } from "react";
import { useLocation } from "react-router-dom";

import { resolveHelpSection } from "@/lib/help-routes";
import { cn } from "@/lib/utils";

import { HelpDrawer } from "./HelpDrawer";
import { useHelp } from "./HelpProvider";

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  if (target.isContentEditable) return true;
  return false;
}

/**
 * Bouton "Aide" injecté en position fixe (top-right) par Layout.
 *
 * - Masqué sur les routes sans aide (login, documentation, inconnue).
 * - Au clic, ouvre le HelpDrawer avec la section correspondante.
 * - Ferme automatiquement le drawer quand la route change (sinon on resterait
 *   avec une aide sur une page qu'on a quittée).
 * - Le raccourci `?` est attaché ici, pas dans HelpProvider, pour ne pas
 *   armer le toggle sur les pages sans aide (où le drawer ne se monte jamais).
 */
export function HelpButton() {
  const location = useLocation();
  const { isOpen, open, close, toggle } = useHelp();
  const section = resolveHelpSection(location.pathname);

  // Fermer le panneau à la navigation pour éviter d'afficher l'aide d'une autre page.
  useEffect(() => {
    close();
  }, [location.pathname, close]);

  // Raccourci `?` — uniquement quand on a une section à afficher.
  useEffect(() => {
    if (!section) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.key !== "?") return;
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      if (isEditableTarget(e.target)) return;
      e.preventDefault();
      toggle();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [section, toggle]);

  if (!section) return null;

  return (
    <>
      <button
        type="button"
        onClick={toggle}
        aria-expanded={isOpen}
        aria-controls="help-drawer"
        aria-label={`Aide sur cette page (${section.title})`}
        className={cn(
          "fixed right-6 top-6 z-40 inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5",
          "border border-line-soft bg-panel text-[12.5px] font-medium text-ink-2 shadow-card",
          "transition-colors hover:bg-panel-2 hover:text-ink",
        )}
      >
        <HelpCircle className="h-4 w-4" aria-hidden />
        <span>Aide</span>
      </button>
      <HelpDrawer
        section={section}
        isOpen={isOpen}
        onOpenChange={(next) => (next ? open() : close())}
      />
    </>
  );
}
```

- [ ] **Step 6.4: Run tests — verify they pass**

Run: `cd frontend && npm test -- src/components/help/HelpButton.test.tsx`
Expected: PASS (7 tests).

- [ ] **Step 6.5: Commit**

```bash
git add frontend/src/components/help/HelpButton.tsx frontend/src/components/help/HelpButton.test.tsx
git commit -m "feat(help): route-aware HelpButton with auto-close on navigation"
```

---

## Task 7: Intégration dans `Layout`

**Files:**
- Modify: `frontend/src/components/Layout.tsx`

Envelopper l'application dans `<HelpProvider>` et placer `<HelpButton>` dans le layout.

- [ ] **Step 7.1: Modifier `Layout.tsx`**

Remplacer le contenu de `frontend/src/components/Layout.tsx` par :

```tsx
import { Outlet } from 'react-router-dom';

import { HelpButton } from '@/components/help/HelpButton';
import { HelpProvider } from '@/components/help/HelpProvider';
import { Sidebar } from '@/components/Sidebar';

export function Layout() {
  return (
    <HelpProvider>
      <div className="flex min-h-screen bg-canvas">
        <Sidebar />
        <main className="flex-1 overflow-x-hidden">
          <div className="mx-auto w-full max-w-[1320px] px-8 py-6">
            <Outlet />
          </div>
        </main>
      </div>
      <HelpButton />
    </HelpProvider>
  );
}
```

`<HelpButton>` est rendu en dehors du conteneur `min-h-screen` parce qu'il est en `fixed` — ne pas le mettre dans `<main>` simplifie son z-index et évite les soucis de stacking context.

- [ ] **Step 7.2: Vérifier que tous les tests passent encore**

Run: `cd frontend && npm test`
Expected: PASS (suite complète, aucune régression).

- [ ] **Step 7.3: Vérifier le typecheck**

Run: `cd frontend && npx tsc -b --noEmit`
Expected: aucune erreur.

- [ ] **Step 7.4: Commit**

```bash
git add frontend/src/components/Layout.tsx
git commit -m "feat(help): wire HelpProvider and HelpButton into Layout"
```

---

## Task 8: Documenter la discipline éditoriale dans `README.md`

**Files:**
- Modify: `README.md` (racine du repo)

Ajouter une section qui rappelle que `documentation.ts` est devenu la source unique pour le contenu d'aide — toute modification de page doit s'y refléter.

- [ ] **Step 8.1: Lire l'état actuel du README**

Run: `cat README.md`

- [ ] **Step 8.2: Ajouter la section après le bloc "Stack"**

Insérer juste avant la section `## Licence` :

```markdown
## Discipline éditoriale

Le fichier `frontend/src/content/documentation.ts` est la **source unique** pour le contenu d'aide affiché à deux endroits :

- la page `/documentation` (guide complet)
- le panneau d'aide latéral (bouton « Aide » en haut à droite, sur chaque page)

**Toute PR qui modifie le comportement d'une page doit mettre à jour la section correspondante de `documentation.ts`** — sinon l'aide affichera une description périmée. Pour raccourcir le contenu dans le panneau sans toucher la doc complète, utiliser le champ optionnel `panel` (cf `DocSectionData`).
```

- [ ] **Step 8.3: Commit**

```bash
git add README.md
git commit -m "docs: add editorial discipline note for documentation.ts"
```

---

## Task 9: Smoke test manuel en dev

Vérifier le rendu visuel et le comportement de bout en bout sur un environnement de développement.

- [ ] **Step 9.1: Lancer la stack dev**

Run: `cd /srv/prod/tools/horizon && docker compose -f docker-compose.dev.yml up -d`
Vérifier : backend sur `http://localhost:8000`, frontend sur `http://localhost:5173`.

- [ ] **Step 9.2: Démarrer le frontend en dev**

Run: `cd /srv/prod/tools/horizon/frontend && npm run dev`
Ouvrir `http://localhost:5173` et se connecter.

- [ ] **Step 9.3: Vérifications manuelles**

Sur **chaque** page de la liste, vérifier :

| Page (route) | Bouton "Aide" visible ? | Au clic : titre attendu dans le panneau |
|---|---|---|
| `/connexion` (avant login) | ❌ NON | — |
| `/tableau-de-bord` | ✅ | Tableau de bord |
| `/analyse` | ✅ | Analyse |
| `/previsionnel` | ✅ | Prévisionnel |
| `/transactions` | ✅ | Transactions |
| `/imports` | ✅ | Imports |
| `/imports/nouveau` | ✅ | Imports (même section) |
| `/engagements` | ✅ | Engagements |
| `/tiers` | ✅ | Tiers |
| `/regles` | ✅ | Règles |
| `/profil` | ✅ | Profil |
| `/administration/utilisateurs` | ✅ | Administration |
| `/administration/societes` | ✅ | Administration |
| `/administration/comptes-bancaires` | ✅ | Administration |
| `/administration/audit` | ✅ | Journal d'audit |
| `/documentation` | ❌ NON | — |

Pour chaque ouverture du panneau, vérifier également :
- Le titre `<h2>` correspond au `title` de la section.
- Les blocs "Ce que vous voyez", "Ce que vous pouvez faire" et (si présents) "Astuces" sont rendus.
- Le lien "Voir le guide complet →" en bas pointe sur `/documentation#<id>` (cliquer pour confirmer la navigation et l'ancre).
- Esc ferme le panneau.
- Clic sur le voile sombre ferme le panneau.
- Cliquer sur le bouton X en haut à droite du panneau ferme le panneau.
- Naviguer vers une autre page avec le panneau ouvert ferme le panneau automatiquement.
- Appuyer sur `?` (sans modifier, focus sur body) ouvre / ferme le panneau.
- Appuyer sur `?` quand le focus est dans un input n'ouvre PAS le panneau (essayer dans la barre de recherche de `/regles` par exemple).

- [ ] **Step 9.4: Si une vérification échoue, ouvrir un correctif ciblé**

Pas d'auto-fix : noter ce qui ne va pas, identifier le composant fautif, ajouter un test qui échoue, fixer, recommit.

- [ ] **Step 9.5: Lancer la suite complète une dernière fois**

```bash
cd frontend && npm test && npx tsc -b --noEmit && npm run build
```

Expected : tous les tests passent, typecheck OK, build prod OK.

- [ ] **Step 9.6: Commit éventuel + push**

Si toutes les vérifications passent, pas de nouveau commit nécessaire (le code est déjà committé task par task). Si tu veux pousser :

```bash
git push origin main
```

---

## Self-Review

Vérifications faites par l'auteur du plan avant remise :

**Couverture du spec** :
- §1 Problème → résolu par l'ensemble (Task 5–7).
- §2 Contraintes / non-buts → respectés (pas de help par champ, pas de feature flag, source unique).
- §3 Décisions retenues → reflétées : overlay (Task 5), bouton injecté Layout (Task 7), source unique avec panel (Task 1+4), couverture (Task 2 mapping).
- §4 Architecture → 1-pour-1 avec File Structure du plan.
- §5 Schéma de données → Task 1.
- §6 Flux d'utilisation → Tasks 3, 5, 6, 7 (Provider + Button + Drawer + Layout).
- §7 Mapping → Task 2.
- §8 Comportements & a11y → Task 6 (close on nav, raccourci `?`, `aria-expanded`, `aria-controls`), Task 5 (X button + Esc gratuit Vaul).
- §9 Tests → couverts dans chaque task TDD.
- §10 Migration éditoriale → aucune (le code retombe sur sees/does/tips si `panel` est absent — testé en Task 4).
- §11 Discipline éditoriale → Task 8.
- §12 Hors scope → respecté (pas de help par champ, pas de mémorisation, pas d'i18n).
- §13 Risques → Vaul direction="right" testé en Task 5 (test de smoke + manuel Task 9).

**Placeholders** : aucun "TODO" / "TBD" / "à compléter" / "similaire à". Tout le code est inline.

**Cohérence des types** : `DocSectionData.panel` (Task 1) est consommé par `HelpContent` (Task 4) avec exactement les mêmes clés (`summary`, `sees`, `does`, `tips`, `hide`). `resolveHelpSection` (Task 2) renvoie `DocSectionData | null` et est consommé par `HelpButton` (Task 6) qui passe à `HelpDrawer` (Task 5) qui accepte `DocSectionData | null`. `useHelp()` (Task 3) renvoie `{ isOpen, open, close, toggle }` et est consommé par `HelpButton` (Task 6) avec ces 4 clés.

**Granularité** : chaque task décompose en 4-6 steps de 2-5 minutes. Pas de step monstre.

---

**Version 1.0 — 2026-04-28**
