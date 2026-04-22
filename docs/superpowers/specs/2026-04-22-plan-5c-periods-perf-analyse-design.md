# Plan 5c — Periods + Perf + Analyse : Design Spec

**Date :** 2026-04-22
**Scope validé :** big bang, 3 parties A+B+C

## Partie A — PeriodSelector partout

**Composant réutilisable** `frontend/src/components/PeriodSelector.tsx` avec :
- **Presets** (boutons) : 30 jours, 90 jours, Année en cours, Mois précédent, 12 mois glissants
- **Personnalisé** : 2 date pickers (natifs HTML5) `from` et `to`
- Interface : `{ value: {from: string, to: string, preset?: string}; onChange: (v) => void }`

**Intégration** :
- **Dashboard** : remplacer les period tabs actuels par le nouveau composant. Endpoint `/api/dashboard/summary?period=X` → passer en `?from&to` (param legacy maintenu pour compat). Sérialisation du preset dans l'URL.
- **Prévisionnel v2** : remplacer la fenêtre hardcodée 15 mois par le PeriodSelector (granularité mois — `YYYY-MM` au lieu de `YYYY-MM-DD`). Variante `<MonthRangeSelector>` dédiée.
- **Historique imports** : ajouter param backend `?from&to` (opérant sur `ImportRecord.created_at` OU `period_start`). Frontend : PeriodSelector.
- **Transactions** : `TransactionFilters.tsx` → remplacer les 2 inputs date par le PeriodSelector (pour cohérence UI). Pas de changement backend (params date_from/date_to existent).

## Partie B — Perf fix `compute_pivot`

**Problème actuel :** `compute_cell` est appelé `N_categories × N_months` fois, chaque appel faisant plusieurs `SELECT` (transactions sum, commitments sum, forecast_entries sum, line fetch).

**Fix :** batch-loading dans `compute_pivot` :
1. **1 requête** : toutes les transactions de (entity, accounts) groupées par (category_id, month) sur plage élargie (24 mois pour supporter AVG_12M + SAME_MONTH_LAST_YEAR)
2. **1 requête** : tous les commitments `pending` de (entity) groupés par (category_id, month)
3. **1 requête** : tous les forecast_entries de (entity) groupés par (category_id, month)
4. **1 requête** : toutes les forecast_lines du scenario

Construire 4 `dict[(category_id, month_iso), Decimal]` en mémoire. `compute_cell` prend alors en option un paramètre `preloaded: Preloaded` avec ces index et fait juste des lookups O(1) + calcul.

Les méthodes `AVG_3M/6M/12M/PREVIOUS_MONTH/SAME_MONTH_LAST_YEAR` utilisent l'index des transactions au lieu de re-requêter. La méthode `FORMULA` recurse via `compute_cell` qui reçoit le même `preloaded`.

**Résultat attendu** : ~750 requêtes → 4 requêtes. Passage de O(N×M) à O(N×M) en CPU pur.

## Partie C — Page `/analyse`

**Sidebar** : nouvel item "Analyse" dans Pilotage, entre Tableau de bord et Transactions.

**Layout** : colonne pleine largeur. Header (h1 + subtitle + `<EntitySelector />` + `<PeriodSelector />`). Contenu = 6 widgets dans une grille 12-cols responsive.

### Widget 1 — Dérives par catégorie (span 12 cols)
- Tableau : Catégorie | Mois courant | Moyenne 3 mois | Écart absolu | Écart % | Statut
- Ligne rouge fond rose-50 si `|écart %| > 20 %` (seuil configurable v2)
- Tri par `|écart %| DESC`
- Limite 15 premières lignes + bouton "Voir tout"
- **Endpoint** : `GET /api/analysis/category-drift?entity_id&seuil_pct=20`

### Widget 2 — Top movers (span 6 cols × 2)
- 2 blocs côte à côte : "+ Augmentations" (rose) et "− Diminutions" (emerald si baisse de charges, rose si baisse de revenus — signal direction)
- Top 5 par catégorie avec sparkline 3 mois
- **Endpoint** : `GET /api/analysis/top-movers?entity_id&period`

### Widget 3 — Burn rate & Runway (span 4)
- Card : burn rate mensuel moyen (sortie - entrée sur 3 mois)
- Runway : solde actuel / burn rate = X mois (en rouge si < 3 mois)
- Graph sparkline solde prévisionnel 6 mois
- **Endpoint** : `GET /api/analysis/runway?entity_id`

### Widget 4 — Year-over-Year (span 8)
- Bars comparatives : chaque mois 2026 vs 2025 (CA + charges), 2 séries empilées
- Tooltip : delta absolu + %
- **Endpoint** : `GET /api/analysis/yoy?entity_id`

### Widget 5 — Concentration clients (span 6)
- Donut : top 5 clients + "Autres", % CA
- Indicateur HHI (indice Herfindahl simplifié) + label "risque faible/moyen/élevé"
- **Endpoint** : `GET /api/analysis/client-concentration?entity_id&period`

### Widget 6 — Comparaison multi-entités (span 6)
- Table : colonnes = entités accessibles, lignes = KPIs (CA, Charges, Variation nette, Solde actuel, Burn rate, Runway)
- N'apparaît que si user a accès à ≥ 2 entités
- **Endpoint** : `GET /api/analysis/entities-comparison?period`

### Design
- Cards : `rounded-xl border border-line-soft bg-panel p-5 shadow-card`
- Numbers : `font-mono tabular-nums`
- Red highlighting : `bg-rose-50 text-rose-900` pour les cellules en alerte
- Pas de gradients, pas de shadows excessives, tokens design B respectés
- Recharts pour tous les graphs

## Tests

Backend : 6 endpoints × ~3 tests chacun = ~18 nouveaux tests
Frontend : smoke tests pour AnalysePage + 1 test pour PeriodSelector

## Non-objectifs

- Pas de seuils configurables par user en v1 (hardcode 20 % pour dérives, 3 mois pour runway)
- Pas de notifications email sur dérives (c'est Plan 6 alertes)
- Pas d'export Excel/PDF des analyses (Plan 7)
