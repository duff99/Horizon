# Audit D — Forecast V2 & Trésorerie
Date : 2026-05-11
Couverture : 2 pages (ForecastV2Page, DashboardPage), 12 endpoints testés, 3 entités

## Synthèse
- 2 bugs **critiques** (donnée incorrecte / action ne fait pas ce qu'elle dit)
- 3 bugs **moyens** (UX dégradée, potentiellement trompeur)
- 1 bug **mineur** (UX cassée sans impact données)
- 4 **observations**

---

## Bugs trouvés (par sévérité décroissante)

### BUG-D-001 (critique) — `delta_vs_prev_month` toujours 0 sur `GET /api/dashboard/bank-balances?entity_id=X`

- **Composant** : `backend/app/api/dashboard.py` — fonction `_compute_bank_state`, lignes 456–490
- **Action testée** : Tableau de bord → widget « Soldes par compte » → colonne « Δ vs mois-1 »
- **Cas reproduisant** : Appeler `GET /api/dashboard/bank-balances?entity_id=2`
- **Résultat attendu** : delta = +799,90 € (7 933,72 - 7 133,82)
- **Résultat observé** : delta = 0,00 €
  ```
  # Preuve SQL
  SELECT period_end, closing_balance FROM imports
  WHERE bank_account_id=2 AND status='completed'
  ORDER BY period_end DESC;
  -- 2026-04-30 → 7933.72
  -- 2026-03-31 → 7133.82
  # La requête prev_rows filtre period_end < first_of_month(today)
  # = period_end < 2026-05-01
  # MAX(period_end) pour ba=2 = 2026-04-30 ← c'est le closing balance courant !
  # prev_balance = current_balance → delta = 0
  ```
- **Cause supposée** : `_compute_bank_state` utilise `first_of_month(date.today())` = 2026-05-01 comme coupure. Or `period_end = 2026-04-30 < 2026-05-01` est TRUE → l'enregistrement du mois précédent est sélectionné comme « prev balance » alors qu'il s'agit du closing balance du mois ACTUEL.
  Le fix correct est `first_of_month(asof_date)` où `asof_date` est la date du dernier import du compte.
  
  **Deuxième problème** (mode « toutes entités ») : `prev_balance_rows` utilise `period_end IN (prev_end_by_ba.values())` sans JOIN sur `bank_account_id`. Quand plusieurs comptes ont des cutoffs distincts, le produit cartésien fait matcher des enregistrements d'un compte sur la date-coupure d'un autre (ex : ba=2 matche à la fois 2026-03-31 de ba=1 et 2026-04-30). Le résultat du dict Python dépend de l'ordre de retour SQL non-garanti.

- **Suggestion de fix** :
  ```python
  # Ligne 457 : remplacer
  first_of_month = today.replace(day=1)
  # par :
  # Pour chaque account, comparer current asof_date vs le mois qui précède ce asof_date
  # → cutoff = first_of_month(asof_date)
  # Réécrire la sous-requête prev avec un JOIN (ba_id, period_end) au lieu de IN()
  ```

---

### BUG-D-002 (critique) — Export CSV pivot ignore le filtre « Comptes »

- **Composant** : `frontend/src/pages/ForecastV2Page.tsx` ligne 241
- **Action testée** : Prévisionnel → Filtrer sur un sous-ensemble de comptes via le popover → Exporter le pivot CSV
- **Cas reproduisant** : Sélectionner entity_id=2, filtrer account_ids=[2] (un seul compte), déclencher l'export CSV
- **Résultat attendu** : Le CSV contient uniquement les flux du compte filtré (correspondant à l'affichage)
- **Résultat observé** : Le CSV contient TOUS les comptes de l'entité
  ```tsx
  // Ligne 241 ForecastV2Page.tsx — URL d'export actuelle :
  url={`/api/forecast/pivot/export?scenario_id=${scenarioId}&entity_id=${effectiveEntityId}&from=${period.from}&to=${period.to}`}
  // Manquant : &accounts=${accountIds?.join(',')}
  ```
- **Cause supposée** : `accountIds` (du store `forecastUi`) est passé à `usePivot` mais oublié dans l'URL du `ExportButton`.
- **Suggestion de fix** :
  ```tsx
  url={`/api/forecast/pivot/export?scenario_id=${scenarioId}&entity_id=${effectiveEntityId}&from=${period.from}&to=${period.to}${accountIds?.length ? `&accounts=${accountIds.join(',')}` : ''}`}
  ```

---

### BUG-D-003 (moyen) — Pivot `closing_balance_projection` exclut silencieusement les transactions non-catégorisées

- **Composant** : `backend/app/services/forecast_engine.py` — `_preload`, ligne 152 (`category_id.is_not(None)`)
- **Action testée** : Prévisionnel → lecture de la ligne « Solde projeté » dans le graphique PivotBars
- **Cas reproduisant** : Entity 1, pivot Feb-Mars 2026
- **Résultat attendu** : Closing projection ≈ 31,10 € (balance réelle en fin mars)
- **Résultat observé** : Closing projection = 3 236,25 € (×100 vs réel)
  ```
  Preuve SQL entité 1 :
  - Transactions catégorisées : net = +33 671 € in / -33 671 € out ≈ nul (approximatif)
  - Transactions non-catégorisées : net = -34 846 € in / +33 671 € out → nul net mais EXCLUES du pivot
  - Écart = 3 236 - 31 = 3 205 € ≈ toutes les transactions non-catégorisées mal comptabilisées
  
  Entité 2 : discrepancy plus faible (2,40 € sur Feb 2026 = 8 txns non-cat)
  ```
- **Cause supposée** : Le moteur pivot filtre `category_id IS NOT NULL`. L'opening balance vient des `ImportRecord.closing_balance` (correct), mais les flux mensuels n'incluent que les catégorisés. Le solde projeté diverge de la réalité en proportion des transactions non-catégorisées.
- **Suggestion de fix** : Ajouter une ligne synthétique « Non catégorisés » dans les résultats du pivot (avec `realized_cents` = Σ transactions sans catégorie, `forecast_cents = 0`) ou afficher un avertissement si `uncategorized_count > 0`.

---

### BUG-D-004 (moyen) — Alerte « import périmé » utilise la date d'upload et non la date de fin de période

- **Composant** : `backend/app/api/dashboard.py` ligne 711 — `(today - b.last_import_at).days > 35`
- **Action testée** : Dashboard → section Alertes → alerte « Aucun import récent »
- **Cas reproduisant** : Entity 1 (period_end = 2026-03-31, upload_at = 2026-04-20, today = 2026-05-11)
- **Résultat attendu** : Alerte « données périmées » (41 jours sans données financières fraîches)
- **Résultat observé** : Aucune alerte (21 jours depuis l'upload < seuil 35 jours)
- **Cause supposée** : `last_import_at` = `MAX(created_at)` (date d'import du fichier) vs `period_end` (date de fin des données financières dans le fichier). Un utilisateur peut uploader aujourd'hui un relevé de mars sans déclencher d'alerte.
- **Suggestion de fix** : Remplacer la condition par `(today - b.asof).days > 35` où `asof = MAX(period_end)` du dernier import COMPLETED.

---

### BUG-D-005 (moyen) — `balance_trend` dans `/api/dashboard/summary` génère des points fictifs jusqu'à `date.today()` pour les entités avec données périmées

- **Composant** : `backend/app/api/dashboard.py` — `_compute_balance_trend`, appelée ligne 232
- **Action testée** : Dashboard → graphique « Solde estimé — 90 derniers jours »
- **Cas reproduisant** : `GET /api/dashboard/summary?period=last_30d&entity_id=1`
- **Résultat attendu** : La courbe s'arrête à la date de la dernière donnée réelle (2026-03-31 pour entity 1)
- **Résultat observé** : 41 points « fantômes » de 2026-04-01 à 2026-05-11, tous à 31,10 € (flatline)
  ```
  balance_trend count=90
  first=2026-02-11, balance=365.41
  last=2026-05-11, balance=31.10
  Points après 2026-03-31 : 41 → pas de données réelles sur cette période
  ```
- **Cause supposée** : `_compute_balance_trend` prend `end_date = period_end` et `total_balance` = dernier closing connu. Quand `period_end = today` mais `latest_import.period_end = 2026-03-31`, la reconstruction génère 41 points fictifs en avant du dernier import (aucune transaction = flatline trompeuse).
- **Suggestion de fix** : Tronquer `end_date = min(period_end, latest_import_period_end)`, ou afficher une zone grisée « Aucune donnée » pour la partie postérieure à `latest_import_period_end`.

---

### BUG-D-006 (mineur) — Bouton « Comparer » visible même quand aucun second scénario n'existe

- **Composant** : `frontend/src/pages/ForecastV2Page.tsx` lignes 122–140 / `frontend/src/components/forecast/ScenarioOverlay.tsx` ligne 80
- **Action testée** : Prévisionnel → clic sur « Comparer » pour entity 1 ou entity 3 (1 seul scénario)
- **Résultat attendu** : Bouton masqué ou désactivé si aucun scénario de comparaison disponible
- **Résultat observé** : Clic affiche un bandeau orange vide (pas de select), UX cassée
- **Cause supposée** : La condition `!noEntity && !noScenario` ne vérifie pas si d'autres scénarios existent. `ScenarioOverlaySelect` retourne `null` silencieusement si la liste est vide.
- **Suggestion de fix** :
  ```tsx
  // Conditionner sur scenarios.length > 1 :
  {!noEntity && !noScenario && (scenariosQuery.data?.length ?? 0) > 1 && (
    <button ...>Comparer</button>
  )}
  ```

---

## Tableau exhaustif des actions testées

| # | Action | Cas | Entité | Attendu | Observé | Verdict |
|---|--------|-----|--------|---------|---------|---------|
| 1 | GET /api/dashboard/summary?period=last_30d | — | 1 | 0 flux (pas de données en avril-mai) | inflows=0, outflows=0 | OK |
| 2 | GET /api/dashboard/summary?period=last_30d | — | 2 | inflows=32878 € | inflows=32878 € | OK |
| 3 | GET /api/dashboard/summary?period=last_30d | — | 3 | 0 flux (mars périmé) | inflows=0 | OK |
| 4 | GET /api/dashboard/summary?period=previous_month | — | 2 | période = Avril 2026 | période = Avril 2026, inflows=131494 € | OK |
| 5 | GET /api/dashboard/summary?from=2026-04-01&to=2026-04-30 | custom | 2 | même que previous_month | identique | OK |
| 6 | GET /api/dashboard/bank-balances | toutes entités | all | delta ba=2 = +799,90 € | delta ba=2 = +799,90 € (par race condition) | BUG-D-001 (non déterministe) |
| 7 | GET /api/dashboard/bank-balances?entity_id=2 | entité unique | 2 | delta = +799,90 € | delta = 0,00 € | **BUG-D-001** |
| 8 | GET /api/dashboard/categories?period=last_30d | — | 2 | top 5 catégories + Autres | 1 income, 6 expense (dont Autres), pct sum=100% | OK |
| 9 | GET /api/dashboard/top-counterparties | — | 2 | top encaissements/décaissements | BNP FACTOR + URSSAF corrects | OK |
| 10 | GET /api/dashboard/alerts | toutes | all | 2 alertes | critical (solde négatif e3) + warning (non-cat) | OK |
| 11 | GET /api/dashboard/alerts?entity_id=1 | entité unique | 1 | alerte non-cat | 79 non-cat warning | OK |
| 12 | GET /api/dashboard/alerts?entity_id=2 | entité unique | 2 | alerte non-cat | 197 non-cat warning | OK |
| 13 | GET /api/dashboard/alerts?entity_id=3 | entité unique | 3 | alerte solde négatif | critical -270,40 € | OK |
| 14 | Alerte import périmé entity 1 | last data 2026-03-31, 41 jours | 1 | alerte stale | aucune alerte (upload 2026-04-20 = 21 j) | **BUG-D-004** |
| 15 | GET /api/dashboard/month-comparison | — | 2 | mai=0, avr=13M€ | mai=0, avr=13 149 478 c | OK |
| 16 | GET /api/dashboard/month-comparison | — | 1 | mai=0, avr=0 | mai=0, avr=0 | OK |
| 17 | balance_trend 90j entity 1 | period=last_30d | 1 | courbe jusqu'à 2026-03-31 | 41 points fictifs jusqu'à 2026-05-11 | **BUG-D-005** |
| 18 | GET /api/treasury/daily-balance?entity_id=1&days=90 | — | 1 | 90 points, no null | 90 points, latest=31.10 €, no null | OK |
| 19 | GET /api/treasury/daily-balance?entity_id=2&days=90 | — | 2 | 90 points, latest=7933.72 € | conforme | OK |
| 20 | GET /api/treasury/daily-balance?entity_id=3&days=90 | — | 3 | 90 points, latest=-270.40 € | conforme | OK |
| 21 | GET /api/treasury/per-account | toutes | all | 3 comptes avec sparkline 30 pts | 3 comptes, variation ba=2 = +79990 c (correct) | OK |
| 22 | GET /api/treasury/per-account?entity_id=2 | unique | 2 | 1 compte, variation=+79990 c | conforme | OK |
| 23 | GET /api/forecast/rolling-13w?entity_id=1&scenario_id=2 | — | 1 | 13 semaines, ancrage 2026-03-31 | W13 (W-1) passé=True, W14 current=False avec realized | OK |
| 24 | GET /api/forecast/rolling-13w?entity_id=2&scenario_id=1 | — | 2 | 13 semaines, ancrage 2026-04-30 | W17 passé, W18 current avec realized=-835799 c | OK |
| 25 | GET /api/forecast/rolling-13w?entity_id=3&scenario_id=3 | — | 3 | 13 semaines | conforme | OK |
| 26 | GET /api/forecast/pivot?scenario_id=1&entity_id=2&from=2026-02&to=2026-06 | — | 2 | 25 lignes catégories, closing cohérent | 25 lignes, opening=452 c, closing[0]=2210 c | OK math |
| 27 | Pivot closing_balance_projection vs réel | Feb 2026 entity 2 | 2 | 19,70 € (closing import) | 22,10 € (diff=2,40 € = txns non-cat) | **BUG-D-003** |
| 28 | Pivot closing_balance_projection vs réel | Mar 2026 entity 1 | 1 | 31,10 € | 3 236,25 € (écart = non-cat) | **BUG-D-003** |
| 29 | GET /api/forecast/pivot/export?scenario_id=1&entity_id=2 | format=csv | 2 | CSV semicolon avec BOM, 25 lignes | conforme (UTF-8-sig, semicolon, 12 cols) | OK |
| 30 | Export avec filtre accounts | accounts=2 filtré | 2 | CSV = données filtrées | CSV = toutes données (filtre ignoré) | **BUG-D-002** |
| 31 | GET /api/forecast/scenarios?entity_id=1 | — | 1 | 1 scénario | id=2 Principal is_default=True | OK |
| 32 | GET /api/forecast/scenarios?entity_id=2 | — | 2 | 2 scénarios | Principal + Scénario redressement | OK |
| 33 | Overlay G7 — entity_id=2 | scenario 1 vs 4 | 2 | 2 courbes différentes | closing[May] 795592 vs 12780388 (différentes) | OK |
| 34 | Overlay G7 — entity_id=1 | 1 seul scénario | 1 | bouton masqué ou désactivé | bouton visible + bandeau vide | **BUG-D-006** |
| 35 | What-if G8 — double-clic cellule future | May 2026, entity 2 | 2 | override local, no DB write | override local visuel, reset fonctionne | OK |
| 36 | What-if G8 — clic cellule passée | Feb 2026 | 2 | non cliquable | non cliquable (clickable=month>=currentMonth) | OK |
| 37 | GET /api/analysis/working-capital?entity_id=1 | — | 1 | has_data=False (aucun engagement) | has_data=False | OK |
| 38 | GET /api/analysis/working-capital?entity_id=2 | — | 2 | has_data=False (1 seul engagement cancelled) | has_data=False | OK |
| 39 | WorkingCapitalBanner ForecastV2Page | — | 1-3 | message amber "Aucun engagement" | message amber affiché | OK |
| 40 | GET /api/forecast/recurring-suggestions?entity_id=2 | — | 2 | 5 suggestions avec average_amount | 5 suggestions, average_amount correct | OK |
| 41 | Entity isolation — categories | entity_id=1 vs entity_id=2 | 1 vs 2 | données disjointes | conforme | OK |
| 42 | Entity isolation — bank-balances | entity_id=1 | 1 | 1 seul compte entity=1 | 1 compte entity=1 seulement | OK |
| 43 | GET /api/forecast/projection?entity_id=2 | — | 2 | starting_balance=7933,72 € | conforme (horizon plat si aucune ForecastLine) | OK |

---

## Couverture

### Pages auditées
- `frontend/src/pages/ForecastV2Page.tsx` ✓
- `frontend/src/pages/DashboardPage.tsx` ✓

### Composants audités
- `frontend/src/components/forecast/WorkingCapitalBanner.tsx` ✓
- `frontend/src/components/forecast/ScenarioOverlay.tsx` ✓
- `frontend/src/components/forecast/PivotTable.tsx` (what-if G8) ✓
- `frontend/src/components/forecast/PivotBars.tsx` ✓
- `frontend/src/components/forecast/Rolling13WChart.tsx` (endpoints vérifiés) ✓

### Endpoints testés (12/12)
| Endpoint | Testé | Statut |
|---|---|---|
| GET /api/dashboard/summary | ✓ | OK |
| GET /api/dashboard/bank-balances | ✓ | **BUG-D-001** |
| GET /api/dashboard/categories | ✓ | OK |
| GET /api/dashboard/top-counterparties | ✓ | OK |
| GET /api/dashboard/alerts | ✓ | **BUG-D-004** |
| GET /api/dashboard/month-comparison | ✓ | OK |
| GET /api/treasury/daily-balance | ✓ | OK |
| GET /api/treasury/per-account | ✓ | OK |
| GET /api/forecast/rolling-13w | ✓ | OK |
| GET /api/forecast/pivot | ✓ | OK (avec note BUG-D-003) |
| GET /api/forecast/pivot/export | ✓ | **BUG-D-002** |
| GET /api/forecast/scenarios | ✓ | OK |
| GET /api/forecast/lines | ✓ | OK |
| GET /api/forecast/projection | ✓ | OK |
| GET /api/forecast/recurring-suggestions | ✓ | OK |
| GET /api/analysis/working-capital | ✓ | OK |

### Non testé (hors scope ou non applicable)
- Click donut → navigation vers Transactions (pas de `onClick` implémenté dans DashboardPage — le donut n'est pas navigable, intentionnel)
- Click top-tier → navigation vers Transactions (idem — top list n'est pas navigable, intentionnel)
- Export XLSX (openpyxl non installé dans le container, 400 attendu et correct)
- Sélection compte bancaire sur Dashboard (pas de filtre compte sur Dashboard, uniquement sur Prévisionnel)

### Observations
1. **G8 what-if** est bien local au navigateur (Map React state, aucune mutation DB). Reset fonctionne. Les mois passés ne sont pas éditables (`clickable = month >= currentMonth`).
2. **Rolling 13W ancrage** : `data_anchor()` correctement utilisé (`today = data_anchor(db, entity_id)`). Le point W-1 est bien passé, W0 est la semaine courante avec realized partiel.
3. **G7 overlay** fonctionne pour entity 2 (2 scénarios) : les deux courbes sont distinctes (`closing[May] = 795 592 c` vs `12 780 388 c`). La fonctionnalité est correcte quand >1 scénario.
4. **dashboard.py** n'utilise pas `data_anchor()` — il utilise `date.today()` partout pour la résolution de période. Ceci est cohérent car le dashboard est intentionnellement ancré sur le calendrier réel (pas sur les données), contrairement à Analyse et Rolling 13W. Le comportement est documenté implicitement via les labels de période.
