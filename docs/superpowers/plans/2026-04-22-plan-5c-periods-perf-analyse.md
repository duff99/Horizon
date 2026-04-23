# Plan 5c — Periods + Perf + Analyse : Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Phases exécutées par 1 subagent chacune.

**Goal:** (A) filtre période personnalisée partout, (B) perf fix forecast pivot, (C) nouvelle page Analyse avec 6 widgets KPI.

**Architecture:** Composant `PeriodSelector` réutilisable côté frontend. Batch-loading des queries dans `compute_pivot` côté backend. Nouveau router `/api/analysis/*` avec 6 endpoints orientés KPI.

**Branche :** `plan-5c-periods-perf-analyse`
**Tag attendu :** `plan-5c-done`

---

## Phase 1 — Perf fix `compute_pivot` (backend)

**Files:**
- Modify: `backend/app/services/forecast_engine.py`
- Test: `backend/tests/services/test_forecast_engine_perf.py` (nouveau)

### Contexte du problème
`compute_pivot` appelle `compute_cell(...)` pour chaque (category, month). Chaque `compute_cell` :
- `_sum_transactions` → 1 SELECT
- `_sum_commitments` → 1 SELECT  
- `_sum_forecast_entries` → 1 SELECT
- Lookup `ForecastLine` → 1 SELECT (parfois hit inutile)
- Si méthode AVG_3M → 3 SELECT de plus
- Si méthode FORMULA → récursion sur d'autres catégories → cascade

Total observable : **~750+ SELECT pour 15 mois × 50 catégories**.

### Solution : `Preloaded` dataclass + batch loading

- [ ] Ajouter dataclass `Preloaded` :
  ```python
  @dataclass
  class Preloaded:
      transactions_by_cat_month: dict[tuple[int, str], int]  # cents
      commitments_by_cat_month: dict[tuple[int, str], int]
      forecast_entries_by_cat_month: dict[tuple[int, str], int]
      lines_by_cat: dict[int, ForecastLine]
      categories_by_name: dict[str, int]  # lowercased trimmed → id
  ```

- [ ] Fonction `_preload(session, entity_id, scenario_id, months_range, account_ids)` :
  - 1 requête : `SELECT category_id, date_trunc('month', operation_date) AS month, SUM(amount_cents_or_converted) FROM transactions JOIN bank_accounts ON ba WHERE ba.entity_id=? AND (ba.id IN account_ids OR account_ids IS NULL) AND operation_date BETWEEN earliest AND latest GROUP BY category_id, month`
  - earliest = `from_month - 12 months` (pour supporter AVG_12M et SAME_MONTH_LAST_YEAR)
  - latest = `to_month + 1 month`
  - Même pattern pour commitments (status=pending, expected_date) et forecast_entries (due_date)
  - Load all lines : `SELECT * FROM forecast_lines WHERE scenario_id = ?`
  - Load categories : `SELECT id, lower(trim(name)) AS key FROM categories`

- [ ] Modifier `compute_cell(session, *, scenario_id, entity_id, category_id, month, preloaded=None)` :
  - Si `preloaded` fourni, utiliser les lookups O(1)
  - Sinon, fallback comportement actuel (requêtes individuelles) pour compat tests unitaires existants

- [ ] Modifier `compute_pivot` : appelle `_preload(...)` une fois au début, puis passe `preloaded` à tous les `compute_cell`

- [ ] Modifier `_evaluate_line` pour accepter `preloaded` et utiliser `preloaded.transactions_by_cat_month` pour les méthodes AVG_N, PREVIOUS_MONTH, SAME_MONTH_LAST_YEAR

- [ ] Test perf : créer un fixture avec 20 catégories × 10 tx/cat/mois × 18 mois = 3600 transactions. Mesurer le nombre de requêtes SQL via event listener SQLAlchemy `before_cursor_execute`. Assertion : `count <= 10` (marge de sécurité sur les 4 attendues).

- [ ] Vérifier que tous les tests Phase 4 existants passent encore (fallback ok).

Commit : `perf(forecast-engine): batch-load transactions/commitments/entries in compute_pivot`

---

## Phase 2 — Backend `/api/analysis/*` endpoints

**Files:**
- Create: `backend/app/api/analysis.py`
- Create: `backend/app/services/analysis.py` (logique métier)
- Create: `backend/app/schemas/analysis.py`
- Create: `backend/tests/api/test_analysis.py`
- Register router in `backend/app/api/router.py`

### Endpoints (pattern d'access check identique aux autres routers)

#### 2.1 `GET /api/analysis/category-drift?entity_id&seuil_pct=20`
Pour chaque catégorie avec activité récente, calculer :
- current_month_cents : somme transactions du mois en cours
- avg_3m_cents : moyenne des 3 mois précédents (hors mois courant)
- delta_cents : current - avg_3m
- delta_pct : (current - avg_3m) / |avg_3m| × 100 (0 si avg_3m == 0)
- status : "alert" si |delta_pct| > seuil_pct, "normal" sinon

Réponse : `{ rows: [{category_id, label, current_cents, avg3m_cents, delta_cents, delta_pct, status}], seuil_pct }`
Tri : `|delta_pct| DESC`.

#### 2.2 `GET /api/analysis/top-movers?entity_id&limit=5`
Pour chaque catégorie, calcul de `delta_vs_prev_month_cents = current_month - previous_month`.
Retourner :
- `increases`: top N catégories avec delta positif (sorties qui montent OU entrées qui montent)
- `decreases`: top N avec delta négatif
- Pour chaque ligne, `sparkline_3m_cents: [int, int, int]` (3 derniers mois finis)

Réponse : `{ increases: [{category_id, label, direction, delta_cents, sparkline: [...]}], decreases: [...] }`

#### 2.3 `GET /api/analysis/runway?entity_id`
- `burn_rate_cents`: moyenne (entries - sorties) sur 3 derniers mois finis. Si négatif → on perd de l'argent.
- `current_balance_cents`: somme des closing_balance du dernier import par compte bancaire de l'entité
- `runway_months`: si burn négatif, `floor(current_balance / |burn_rate|)`. Sinon None (pas de burn).
- `forecast_balance_6m_cents`: list[int] de 6 valeurs = projection solde fin de mois sur 6 mois (utilisant scenario par défaut + moyenne)
- `status`: "critical" si runway < 3, "warning" si < 6, "ok" sinon

Réponse : `{ burn_rate_cents, current_balance_cents, runway_months, forecast_balance_6m_cents: [...], status }`

#### 2.4 `GET /api/analysis/yoy?entity_id`
Comparaison Y vs Y-1 sur les 12 mois glissants :
- Pour chaque mois des 12 derniers, somme des entrées + sorties cette année et l'année précédente

Réponse : `{ months: ["2025-05", ..., "2026-04"], series: [{month, revenues_current, revenues_previous, expenses_current, expenses_previous}] }`

#### 2.5 `GET /api/analysis/client-concentration?entity_id&months=12`
Sur les N derniers mois, somme du CA encaissé par tiers (counterparty) :
- Top 5 + "Autres"
- `hhi`: Herfindahl index = Σ(share²) × 10000, scale 0-10000
- `risk_level`: "low" si hhi < 1500, "medium" < 2500, "high" sinon

Réponse : `{ total_revenue_cents, top5: [{counterparty_id, name, amount_cents, share_pct}], others_cents, others_share_pct, hhi, risk_level }`

#### 2.6 `GET /api/analysis/entities-comparison?months=1`
Pour **toutes les entités accessibles au user** :
- `revenues_cents`, `expenses_cents` sur la période (mois courant si months=1)
- `net_variation_cents` = rev - exp
- `current_balance_cents`
- `burn_rate_cents` (3m rolling)
- `runway_months`

Réponse : `{ entities: [{entity_id, name, revenues_cents, expenses_cents, net_variation_cents, current_balance_cents, burn_rate_cents, runway_months}] }`

### Tests (3 par endpoint minimum)
- happy path avec fixtures
- 403 si entity_id non accessible
- cas limites : pas de données → réponse vide cohérente

### Commits
- `feat(analysis): category drift endpoint`
- `feat(analysis): top movers + runway endpoints`
- `feat(analysis): yoy + client concentration endpoints`
- `feat(analysis): entities comparison endpoint`

(ou regroupés en 1-2 commits si plus naturel)

---

## Phase 3 — Frontend `<PeriodSelector />` + intégrations

**Files:**
- Create: `frontend/src/components/PeriodSelector.tsx`
- Create: `frontend/src/test/PeriodSelector.test.tsx`
- Modify: `frontend/src/pages/DashboardPage.tsx` (remplacer period tabs)
- Modify: `frontend/src/pages/ForecastV2Page.tsx` (ajouter MonthRangeSelector ou étendre PeriodSelector)
- Modify: `frontend/src/pages/ImportHistoryPage.tsx` (ajouter)
- Modify: `frontend/src/components/TransactionFilters.tsx` (remplacer 2 inputs date par PeriodSelector)
- Modify: `backend/app/api/imports.py` (ajouter params `from`, `to`)

### `PeriodSelector.tsx`

```tsx
type Preset = "30d" | "90d" | "ytd" | "previous_month" | "12m" | "custom";

export interface PeriodValue {
  from: string; // YYYY-MM-DD
  to: string;
  preset: Preset;
}

interface Props {
  value: PeriodValue;
  onChange: (v: PeriodValue) => void;
  granularity?: "day" | "month";  // défaut day
}

export function PeriodSelector({ value, onChange, granularity = "day" }: Props) {
  // UI : boutons presets dans une row + si preset === "custom", afficher 2 date pickers
  // Style : h-9, bg-panel, shadow-card, border-line-soft (cohérent EntitySelector)
}
```

Helpers :
- `computeRange(preset: Preset, today: Date): {from, to}` — calcule les bornes
- `formatForDisplay(value): string` — résumé FR ("30 derniers jours", "Avr. 2026", "Personnalisé 01/01 → 15/04")

Test : setPreset("30d") → onChange called with correct from/to. Custom range valide.

### MonthRangeSelector

Pour Forecast v2, on veut granularité mois (15 mois glissants par défaut). Créer une variante légère ou un mode `granularity="month"` dans le même composant.

### Dashboard

Remplacer :
```
<div role="tablist" aria-label="Période" className="inline-flex rounded-md border...">
  {PERIODS.map(...)}
</div>
```
par :
```tsx
<PeriodSelector value={period} onChange={setPeriod} />
```

Adapter l'endpoint : `/api/dashboard/summary?from=YYYY-MM-DD&to=YYYY-MM-DD`. Vérifier si les endpoints acceptent déjà `from/to` (je pense oui, via computed period). Si non, ajouter un fallback backend.

### Forecast v2

Ajouter le selector dans le header à côté des autres contrôles. Le `usePivot` consomme `from, to` en YYYY-MM. Le MonthRangeSelector doit retourner ce format.

### Imports

Backend : `GET /api/imports?entity_id&from&to` avec filtre sur `ImportRecord.period_start/period_end` (ou `created_at` en fallback). Frontend : PeriodSelector dans le header.

### Transactions

Remplacer les 2 inputs date dans `TransactionFilters.tsx` par un `<PeriodSelector />`. Garder les params backend identiques (`date_from`, `date_to`).

Commits (groupés par changement logique) :
- `feat(components): reusable PeriodSelector with presets + custom range`
- `feat(dashboard): use PeriodSelector`
- `feat(forecast): period range control in header`
- `feat(imports): backend from/to filter + frontend PeriodSelector`
- `refactor(transactions): use PeriodSelector for date range`

---

## Phase 4 — Frontend page `/analyse`

**Files:**
- Create: `frontend/src/api/analysis.ts`
- Create: `frontend/src/types/analysis.ts`
- Create: `frontend/src/pages/AnalysePage.tsx`
- Create: `frontend/src/components/analyse/CategoryDriftTable.tsx`
- Create: `frontend/src/components/analyse/TopMoversCard.tsx`
- Create: `frontend/src/components/analyse/RunwayCard.tsx`
- Create: `frontend/src/components/analyse/YoYChart.tsx`
- Create: `frontend/src/components/analyse/ClientConcentrationCard.tsx`
- Create: `frontend/src/components/analyse/EntitiesComparisonTable.tsx`
- Create: `frontend/src/test/AnalysePage.test.tsx`
- Modify: `frontend/src/router.tsx` (route `/analyse`)
- Modify: `frontend/src/components/Sidebar.tsx` (item "Analyse" dans Pilotage, entre "Tableau de bord" et "Transactions")

### Types miroir endpoints
(voir spec Partie C)

### Hooks TanStack Query
- `useCategoryDrift({entityId, seuilPct?})`
- `useTopMovers({entityId, limit?})`
- `useRunway({entityId})`
- `useYoY({entityId})`
- `useClientConcentration({entityId, months?})`
- `useEntitiesComparison({months?})`

### AnalysePage layout

```tsx
<section className="space-y-6">
  <Header h1="Analyse" subtitle="Indicateurs clés et dérives" + EntitySelector + PeriodSelector />

  <div className="grid grid-cols-12 gap-4">
    <div className="col-span-12"><CategoryDriftTable /></div>
    <div className="col-span-12 md:col-span-6"><TopMoversCard /></div>
    <div className="col-span-12 md:col-span-6"><RunwayCard /></div>
    <div className="col-span-12 md:col-span-8"><YoYChart /></div>
    <div className="col-span-12 md:col-span-4"><ClientConcentrationCard /></div>
    <div className="col-span-12"><EntitiesComparisonTable /></div>  {/* Masqué si user n'a accès qu'à 1 entité */}
  </div>
</section>
```

### Composants — règles design (strict)
- `rounded-xl border border-line-soft bg-panel p-5 shadow-card`
- Header de widget : `text-[15px] font-semibold text-ink` + subtitle `text-[12.5px] text-muted-foreground mt-0.5`
- Nombres : `font-mono tabular-nums`
- Cellules alert : `bg-rose-50 text-rose-900` (pas de rouge vif)
- Charts recharts, pas de gradients, couleurs sobres (emerald-600, rose-600, slate-600)
- Loading : skeleton grid bars pas de spinner circulaire

### Détails par widget

**CategoryDriftTable**
- Props : `{ data: CategoryDriftResponse }`
- Table 6 colonnes : Catégorie, Mois courant, Moyenne 3m, Écart €, Écart %, Statut (badge)
- Ligne alert : classe `bg-rose-50`
- Max 15 rows visible, bouton "Voir tout" qui enlève la limite

**TopMoversCard**
- 2 colonnes : "Plus fortes hausses" / "Plus fortes baisses"
- Chaque entrée : label catégorie + delta € (mono) + sparkline 3 mois (`LineChart` mini-height 32, stroke emerald/rose selon direction)

**RunwayCard**
- KPI en grand (80px font-semibold) : `X mois` avec label "Runway" en dessous
- Sous : Burn rate mensuel (mono) + Solde actuel (mono)
- Sparkline 6 mois prévisionnels en bas
- Couleur fond selon status : "critical" → ring-2 ring-rose-400, "warning" → ring-rose-200, "ok" → default

**YoYChart**
- ComposedChart recharts
- 4 dataKeys : revenues_current, revenues_previous, expenses_current, expenses_previous
- Courant plein, précédent hachuré
- Tooltip : delta absolu + % entre courant et précédent

**ClientConcentrationCard**
- Donut recharts : 6 slices (top 5 + Autres)
- Au centre : valeur du HHI et label risk_level en couleur (emerald/amber/rose)
- Légende à droite avec pourcentages

**EntitiesComparisonTable**
- Table : colonnes = entités, lignes = KPIs
- Si user a seulement 1 entity accessible, ne pas rendre le widget (`return null`)
- Format chiffres FR-fr

### Tests
Smoke test `AnalysePage.test.tsx` : mock tous les hooks, rendu de la page sans crash. Mock minimal.

### Commits
- `feat(analyse): api hooks + types`
- `feat(analyse): CategoryDriftTable + TopMoversCard`
- `feat(analyse): RunwayCard + YoYChart`
- `feat(analyse): ClientConcentrationCard + EntitiesComparisonTable`
- `feat(analyse): /analyse page + sidebar entry`

---

## Phase 5 — E2E + merge + deploy

- [ ] `cd backend && uv run pytest tests/ -q 2>&1 | tail -5` — tout vert
- [ ] `cd frontend && pnpm run test -- --run 2>&1 | tail -5` — tout vert
- [ ] `pnpm run build` — OK
- [ ] `git checkout main && git merge --no-ff plan-5c-periods-perf-analyse -m "merge: plan-5c — periods + perf + analyse"`
- [ ] `git tag plan-5c-done && git push origin main --tags`
- [ ] `docker compose -f docker-compose.prod.yml up -d --build`
- [ ] `curl https://horizon.acreedconsulting.com/readyz` = 200
- [ ] Test manuel :
  - Forecast pivot charge en < 1s (perf fix)
  - PeriodSelector fonctionne sur Dashboard/Forecast/Imports/Transactions
  - Page `/analyse` charge avec les 6 widgets
  - Cellule en alerte dans CategoryDriftTable apparaît en rose si déviation > 20 %

## Self-Review

- Part A (PeriodSelector) → Phase 3 ✅
- Part B (perf fix) → Phase 1 ✅
- Part C (Analyse page) → Phases 2 + 4 ✅
- Design tokens respectés partout (mentionné dans chaque composant)
- Tests attendus : ~18 backend + 2-3 frontend

## Notes d'exécution

1 subagent par phase (Phases 1, 2, 3, 4). Phase 5 en main agent direct. Dispatchés séquentiellement (pas en parallèle : Phase 2 dépend de Phase 1, Phase 4 dépend de Phases 2+3).
