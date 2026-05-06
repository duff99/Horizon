# Horizon — Notes d'équipe

## Documentation d'impact obligatoire

Toute nouvelle action UI à effet (création, modification, suppression
d'état, déclenchement d'un workflow) doit livrer dans la même PR :

1. Un bandeau d'introduction permanent sur la page concernée si le concept est nouveau
2. Un tooltip "?" sur l'action elle-même (composant `<HelpTooltip>` ou équivalent), expliquant en une phrase ce qu'elle déclenche
3. Une section dans `frontend/src/content/documentation.ts` au format `FeatureDoc` :
   - "À quoi ça sert" (intention métier)
   - "Ce que ça change quand tu cliques" (effets backend + UI)
   - "Ce que ça ne change pas" (pour casser les fausses intuitions)
   - "Quand l'utiliser" (cas d'usage typiques)

Une PR sans ces trois éléments est incomplète.
