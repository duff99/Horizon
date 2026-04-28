import { DOC_SECTIONS, type DocSectionData } from "@/content/documentation";

/**
 * Mapping route → sectionId. L'ordre est significatif : le premier match gagne.
 * `/administration/audit` doit précéder `/administration` car c'est plus spécifique.
 *
 * INVARIANT : chaque `sectionId` listé ici DOIT exister dans `DOC_SECTIONS`
 * ET être rendu comme ancre `id=` par `DocumentationPage` (sinon le lien
 * "Voir le guide complet →" du panneau aboutira sur une page sans cible).
 * Si tu ajoutes une route ici, vérifie ces deux conditions.
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
