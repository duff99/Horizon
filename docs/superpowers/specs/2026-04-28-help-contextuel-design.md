# Aide contextuelle in-page — Design

**Date** : 2026-04-28
**Auteur** : Claude (Opus 4.7) avec tdufr
**Statut** : Draft pour relecture utilisateur

---

## 1. Problème

`DocumentationPage` (`/documentation`) contient déjà un guide complet de chaque page de Horizon — structuré en 13 sections (`sees / does / tips`). Mais elle est mono-page : pour consulter l'aide pendant qu'on remplit, par exemple, le formulaire de création d'une règle, il faut quitter la page courante, lire l'aide, et revenir — moment où l'aide n'est plus visible. Friction réelle, qui pousse à ne pas consulter l'aide du tout.

**But** : permettre à l'utilisateur de consulter l'aide *sans quitter* la page courante, sur toutes les pages métier de l'application.

## 2. Contraintes & non-buts

- **Pas de réécriture du contenu existant** : `documentation.ts` reste source unique. Le panneau d'aide réutilise le contenu déjà rédigé.
- **Granularité variable selon la page** : Transactions = page de consultation, peu de besoin d'explications ; Règles ou Engagements = manipulations complexes, plus d'aide nécessaire. Le mécanisme doit permettre de raccourcir par page sans dupliquer la source.
- **Pas de help par champ** (pas de `?` à côté de chaque input). Une seule entrée d'aide par page, contenant tout ce qu'il faut savoir sur cet écran. Pourra être affiné plus tard si besoin.
- **Pas de feature flag** : déploiement direct. Le bouton est invisible sur les pages sans aide, donc rien à activer.

## 3. Décisions retenues (ce qui a été tranché en brainstorming)

| Question | Choix | Raison |
|---|---|---|
| Pattern UI | **Overlay latéral droit** (panneau qui glisse depuis la droite, voile semi-transparent sur le reste) | Marche partout, simple, ne demande pas d'espace permanent dans la grille. Plus simple à implémenter qu'un split-view (option B écartée) tout en couvrant le besoin "voir l'aide à côté du formulaire". |
| Emplacement du déclencheur | **Bouton "Aide" injecté par `Layout`, en haut à droite de la zone main** | Une seule modification (Layout.tsx), route-aware naturellement, ne pollue aucune page. Le groupe "Aide" de la sidebar (vers `/documentation`) reste pour le guide complet. |
| Source du contenu | **`documentation.ts` reste source unique, avec un champ optionnel `panel` par section** | Une seule source de vérité, divergence impossible. Pour les pages où le contenu doit être plus succinct dans le panneau, on définit `panel: { ... }` qui override (Transactions notamment). Sinon, fallback automatique sur `sees / does / tips`. |
| Couverture | **11 sections de page ↔ 11 routes métier** | Mapping quasi 1-pour-1. `/imports` et `/imports/nouveau` partagent la section `imports` ; les 3 pages `/administration/*` (sauf audit) partagent `administration`. `/connexion` et `/documentation` n'ont pas de bouton. Les 2 sections transverses de `documentation.ts` (`premiers-pas`, `securite`) ne sont pas attachées à une route — elles restent accessibles uniquement via `/documentation`. |

## 4. Architecture

```
src/
├── content/documentation.ts         # étendu : champ optionnel `panel` sur DocSectionData
├── components/help/
│   ├── HelpProvider.tsx             # contexte React (open state, méthodes open/close)
│   ├── HelpButton.tsx               # bouton "Aide" rendu par Layout, route-aware
│   ├── HelpDrawer.tsx               # wrapper Vaul direction="right", largeur ~420px
│   └── HelpContent.tsx              # rendu d'une section (summary, sees, does, tips, lien doc)
├── lib/help-routes.ts               # mapping route → sectionId, fonction resolveHelpSection
└── components/Layout.tsx            # MODIFIÉ : enveloppe l'app dans HelpProvider, place HelpButton
```

**Pourquoi un Provider** plutôt qu'un état local dans Layout : permet d'ouvrir le panneau depuis n'importe quel composant (toast d'erreur, lien "Voir l'aide" dans une page) sans drilling de props.

**Pourquoi Vaul `direction="right"`** plutôt qu'ajouter le composant `Sheet` shadcn : Vaul est déjà installé (utilisé par `RuleForm`), supporte nativement les drawers latéraux, gère focus-trap / Esc / ARIA gratuitement. Pas de nouvelle dépendance, cohérence visuelle avec les drawers existants.

## 5. Schéma de données

```ts
// src/content/documentation.ts (extension non-breaking)

export interface DocSectionData {
  id: string;
  title: string;
  subtitle: string;
  sees: string[];
  does: string[];
  tips?: string[];
  /** Override optionnel pour le panneau d'aide contextuel.
   *  Si absent, le panneau réutilise subtitle / sees / does / tips. */
  panel?: {
    summary?: string;                            // remplace subtitle dans le panneau
    sees?: string[];                             // si défini, remplace sees
    does?: string[];                             // idem
    tips?: string[];                             // idem
    hide?: ("sees" | "does" | "tips")[];         // pour cacher un bloc entier dans le panneau
  };
}
```

L'extension est strictement additive — toutes les sections existantes continuent de marcher sans modification.

## 6. Flux d'utilisation

1. Au premier rendu, `Layout` enveloppe l'app dans `<HelpProvider>` et place `<HelpButton>` en haut à droite de la zone main.
2. `HelpButton` lit `useLocation()`, calcule la section via `resolveHelpSection(pathname)`. Si null → bouton non rendu (Login, Documentation).
3. Clic ou raccourci `?` → `HelpProvider` passe `isOpen=true`.
4. `HelpDrawer` se rend, prend ~420px à droite (full-width sous 640px), pose un voile sur le reste. Le focus va dans le panneau, le contenu derrière reste visible mais inactif.
5. `HelpContent` rend la section : titre, summary (override `panel.summary` ou fallback `subtitle`), puis blocs `sees`, `does`, `tips` (overrides du `panel` appliqués si présents). En bas : lien "Voir le guide complet →" pointant vers `/documentation#<sectionId>`.
6. Esc, clic dehors, bouton X, ou navigation vers une autre route → ferme.

## 7. Mapping des routes

```ts
// src/lib/help-routes.ts

const HELP_ROUTES: { match: RegExp; sectionId: string }[] = [
  { match: /^\/tableau-de-bord/, sectionId: "tableau-de-bord" },
  { match: /^\/analyse/,         sectionId: "analyse" },
  { match: /^\/previsionnel/,    sectionId: "previsionnel" },
  { match: /^\/transactions/,    sectionId: "transactions" },
  { match: /^\/imports/,         sectionId: "imports" },
  { match: /^\/engagements/,     sectionId: "engagements" },
  { match: /^\/tiers/,           sectionId: "tiers" },
  { match: /^\/regles/,          sectionId: "regles" },
  { match: /^\/profil/,          sectionId: "profil" },
  { match: /^\/administration\/audit/, sectionId: "audit" },     // AVANT /administration
  { match: /^\/administration/,  sectionId: "administration" },
];

export function resolveHelpSection(pathname: string): DocSectionData | null {
  const hit = HELP_ROUTES.find((r) => r.match.test(pathname));
  if (!hit) return null;
  return DOC_SECTIONS.find((s) => s.id === hit.sectionId) ?? null;
}
```

L'ordre des entrées est significatif (le premier match gagne) — `/administration/audit` avant `/administration`.

## 8. Comportements & accessibilité

- **Fermeture à la navigation** : un effet écoute `useLocation` et ferme le panneau au changement de route. Sinon, on resterait avec un panneau ouvert affichant l'aide d'une page qu'on a quittée.
- **Pas de mémorisation** entre sessions / rechargements (sobriété — re-cliquer est trivial).
- **Raccourci clavier** : touche `?` (sans modifier) ouvre / ferme le panneau. Désactivé quand le focus est dans un `<input>`, `<textarea>`, ou un `contenteditable`.
- **A11y** :
  - `HelpDrawer` hérite du focus trap et du retour de focus de Vaul/Radix.
  - `HelpButton` a `aria-expanded`, `aria-controls="help-panel"`, label visible ("Aide" + icône `HelpCircle`).
  - Le panneau a `role="dialog"`, `aria-labelledby` pointant le `<h2>` du titre.

## 9. Tests

Écrits en TDD (cf `superpowers:test-driven-development`). Vitest + Testing Library, mêmes conventions que le code existant (`RuleForm.test.tsx`, etc.).

| Fichier | Cas testés |
|---|---|
| `lib/help-routes.test.ts` | `resolveHelpSection("/regles")` → section "regles" ; `/connexion` → null ; `/administration/audit` matche "audit" et pas "administration" (ordre) ; `/imports/nouveau` matche "imports" ; chemin inconnu → null |
| `components/help/HelpDrawer.test.tsx` | Rendu du title et de la summary ; override `panel.sees` appliqué ; override `panel.hide=["tips"]` cache le bloc ; Esc ferme ; clic sur X ferme |
| `components/help/HelpButton.test.tsx` | Pas rendu sur `/connexion` ni `/documentation` ; rendu sur `/regles` ; `aria-expanded` toggle au clic |

## 10. Migration éditoriale

Aucune. Le premier déploiement laisse les 13 sections de `documentation.ts` strictement inchangées — le panneau les rend telles quelles via le fallback. tdufr peut ensuite, page par page et au fil de l'eau, ajouter un `panel: { summary, ... }` là où c'est pertinent (typiquement `transactions`, `tiers`, `audit` pour les raccourcir ; `regles`, `engagements` resteront sans doute sur le contenu complet).

## 11. Discipline éditoriale

`documentation.ts` devient le **contrat** entre le code et l'utilisateur. Conséquence : toute PR qui modifie le comportement d'une page doit aussi mettre à jour la section correspondante.

Plan progressif :
- **Maintenant** : règle ajoutée à `README.md` racine (section dédiée "Discipline éditoriale") — *"toute modification d'une page doit se refléter dans `src/content/documentation.ts`"*.
- **Plus tard (si besoin)** : check léger en CI (lint custom) qui rappelle la règle quand un fichier de page (`src/pages/*.tsx`) est touché sans que `documentation.ts` ne le soit. Hors scope du présent spec.

## 12. Hors scope (à reconsidérer plus tard si besoin)

- Aide par champ (`?` à côté d'un input) — pour l'instant, le panneau global suffit.
- Mémorisation de l'état ouvert/fermé entre navigations.
- Lien profond `?help=open` dans l'URL pour partager un lien "ouvre cette page avec l'aide ouverte".
- Recherche dans le panneau (la page `/documentation` reste l'endroit pour rechercher).
- Vidéos / GIF / illustrations — texte seul pour ce premier jet.
- Internationalisation — Horizon est 100% français aujourd'hui (cf PROGRESS.md), pas de besoin i18n.

## 13. Risques

- **Désynchronisation contenu / code** : si une feature change sans mettre à jour `documentation.ts`, le panneau affichera de l'aide périmée — c'est pire qu'une absence d'aide. Mitigation : règle éditoriale §11, à durcir en lint CI plus tard.
- **Largeur 420px sur écran moyen (~1280px)** : le panneau couvre une part significative du contenu. Acceptable pour la lecture courte, mais sur Dashboard où il y a beaucoup de graphes, le voile cache le contenu sous-jacent. C'est le compromis du choix overlay (vs split-view écarté) — assumé.
- **Vaul `direction="right"`** : l'API existe mais on ne l'a pas encore utilisée dans le projet (seul `direction="bottom"` actuellement). Test manuel + tests unitaires nécessaires.

---

**Version 1.0 — 2026-04-28**
