# Plan 5b — Forecast v2 Agicap-like : Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Porter le module Prévisionnel d'Horizon au niveau d'Agicap : tableau pivot catégories × mois, modes Payées/Engagées/Prévisionnel, méthodes de calcul configurables, scénarios multiples, vue consolidée comptes, module Engagements.

**Architecture:** 3 nouvelles tables (`commitment`, `forecast_scenario`, `forecast_line`) + moteur de calcul à la volée + parser DSL simple + endpoints REST + nouvelles pages React avec design-taste-frontend tokens. Approche hybride : règles stockées, calcul on-demand, cache HTTP court (30s).

**Tech Stack:** FastAPI + SQLAlchemy 2.0 + Alembic + pytest (backend). React + TS + TanStack Query + Zustand + recharts + shadcn/ui (frontend). Design skills : `design-taste-frontend` + `gpt-taste`.

**Spec de référence :** `docs/superpowers/specs/2026-04-22-plan-5b-forecast-v2-design.md`
**Branche :** `plan-5b-forecast-v2`
**Tag attendu :** `plan-5b-done`

---

## Structure des fichiers

### Backend (nouveaux)
```
backend/app/models/commitment.py
backend/app/models/forecast_scenario.py
backend/app/models/forecast_line.py
backend/app/schemas/commitment.py
backend/app/schemas/forecast.py                      (étendu : Scenario, Line, Pivot)
backend/app/api/commitments.py
backend/app/api/forecast_scenarios.py
backend/app/api/forecast_lines.py
backend/app/api/forecast_pivot.py                    (endpoint /pivot uniquement)
backend/app/services/forecast_engine.py              (moteur de calcul + méthodes)
backend/app/services/formula_parser.py               (DSL parser)
backend/app/services/commitment_matching.py          (matching auto à l'import)
backend/alembic/versions/NNNN_add_commitments_and_forecast_v2.py

backend/tests/api/test_commitments.py
backend/tests/api/test_forecast_scenarios.py
backend/tests/api/test_forecast_lines.py
backend/tests/api/test_forecast_pivot.py
backend/tests/api/test_dashboard_month_comparison.py
backend/tests/services/test_forecast_engine.py
backend/tests/services/test_formula_parser.py
backend/tests/services/test_commitment_matching.py
```

### Backend (modifiés)
```
backend/app/models/__init__.py                       (exporter les 3 nouveaux)
backend/app/main.py                                  (register 4 nouveaux routers)
backend/app/services/imports.py                      (appel commitment_matching après insert tx)
backend/app/api/dashboard.py                         (endpoint /month-comparison)
```

### Frontend (nouveaux)
```
frontend/src/api/commitments.ts
frontend/src/api/forecastScenarios.ts
frontend/src/api/forecastLines.ts
frontend/src/api/forecastPivot.ts
frontend/src/api/dashboardComparison.ts

frontend/src/pages/CommitmentsPage.tsx
frontend/src/pages/CommitmentMatchDialog.tsx
frontend/src/pages/CommitmentFormDialog.tsx
frontend/src/pages/ForecastV2Page.tsx                (remplace ForecastPage.tsx dans le router)

frontend/src/components/forecast/PivotTable.tsx
frontend/src/components/forecast/PivotBars.tsx
frontend/src/components/forecast/CellEditorDrawer.tsx
frontend/src/components/forecast/ScenarioSelector.tsx
frontend/src/components/forecast/ConsolidatedAccountsPopover.tsx
frontend/src/components/forecast/MethodForm.tsx      (form radio méthode + sous-options)
frontend/src/components/dashboard/MonthComparisonCard.tsx

frontend/src/types/forecast.ts                       (types partagés pivot/line/scenario)

frontend/src/test/CommitmentsPage.test.tsx
frontend/src/test/forecast/PivotTable.test.tsx
frontend/src/test/forecast/CellEditorDrawer.test.tsx
frontend/src/test/forecast/formulaValidation.test.ts
```

### Frontend (modifiés)
```
frontend/src/components/Sidebar.tsx                  (item "Engagements")
frontend/src/router.tsx                              (routes /engagements + remplacer /previsionnel)
frontend/src/pages/DashboardPage.tsx                 (ajouter MonthComparisonCard)
```

---

## Phase 1 — Engagements backend

### Task 1.1 : Modèle `Commitment` + enum `CommitmentStatus`, `CommitmentDirection`

**Files:**
- Create: `backend/app/models/commitment.py`
- Modify: `backend/app/models/__init__.py` (export)

- [ ] Écrire le modèle. Utiliser `Integer` pour `amount_cents` (toujours positif, direction portée par l'enum). Relations : `entity` (many-to-one), `counterparty` (many-to-one nullable), `category` (many-to-one nullable), `bank_account` (many-to-one nullable), `matched_transaction` (many-to-one nullable), `created_by` (many-to-one User). Colonne `pdf_attachment_id FK imports.id nullable` (réutilise le stockage PDF d'imports pour les factures).
- [ ] Exporter dans `__init__.py`
- [ ] Commit : `feat(models): Commitment + enums`

### Task 1.2 : Migration Alembic

**Files:**
- Create: `backend/alembic/versions/<timestamp>_add_commitments_and_forecast_v2.py`

Regrouper toutes les créations de tables du plan (commitments, forecast_scenarios, forecast_lines) dans **une seule migration** pour éviter les conflits de séquence.

- [ ] Générer avec `cd backend && uv run alembic revision -m "add_commitments_and_forecast_v2"`
- [ ] Remplir `upgrade()` :
  - `op.create_table("commitments", …)` avec toutes les colonnes du design
  - `op.create_table("forecast_scenarios", …)` (cf. Phase 3)
  - `op.create_table("forecast_lines", …)` (cf. Phase 3)
  - Index : `ix_commitments_entity_status (entity_id, status)`, `ix_commitments_expected_date`, `ix_commitments_matched_transaction_id`
  - Unique partiel : `CREATE UNIQUE INDEX uq_forecast_scenario_default_per_entity ON forecast_scenarios (entity_id) WHERE is_default = true`
  - Unique : `uq_forecast_line_scenario_category (scenario_id, category_id)`
- [ ] Remplir `downgrade()` : drop inverse
- [ ] Run `cd backend && uv run alembic upgrade head` — doit réussir sur la base de test
- [ ] Commit : `feat(migrations): add commitments + forecast scenarios + forecast lines`

### Task 1.3 : Schemas Pydantic Commitment

**Files:**
- Create: `backend/app/schemas/commitment.py`

- [ ] Définir `CommitmentRead`, `CommitmentCreate`, `CommitmentUpdate`, `CommitmentMatchRequest(transaction_id: int)`, `CommitmentSuggestionResponse(candidates: list[TransactionBrief])`. Inclure les champs `counterparty_name` et `category_name` dénormalisés dans `CommitmentRead` via computed properties.
- [ ] Commit : `feat(schemas): commitment payloads`

### Task 1.4 : Endpoints CRUD commitments

**Files:**
- Create: `backend/app/api/commitments.py`
- Modify: `backend/app/main.py` (include_router)

- [ ] TDD pour chaque endpoint (test d'abord, fail, implémenter, pass, commit) :
  - `GET /api/commitments?entity_id&status&from&to&direction&page&per_page` — pagination + filtres (pattern calqué sur `/api/transactions`). Access check via `UserEntityAccess`.
  - `POST /api/commitments` — validation montant > 0, date cohérente (issue_date <= expected_date + 365j). `require_entity_access`.
  - `GET /api/commitments/{id}` — 404 si non trouvé, 403 si entité non accessible
  - `PATCH /api/commitments/{id}`
  - `DELETE /api/commitments/{id}` — soft-delete via `status=cancelled` (ne pas delete physique, pour audit)
- [ ] Commit par endpoint : `feat(api/commitments): GET list`, `feat(api/commitments): POST create`, etc.

### Task 1.5 : Endpoints match / unmatch / suggest

**Files:**
- Modify: `backend/app/api/commitments.py`
- Create: `backend/app/services/commitment_matching.py`

- [ ] Dans le service, fonction `suggest_matches(session, commitment, limit=10)` qui retourne la liste des tx candidates triées par score :
  - Filtre : `entity_id` identique (via bank_account.entity_id), `direction` identique (sign of amount), pas déjà matchée, `operation_date` dans `[expected_date - 7j, expected_date + 7j]`
  - Score = `100 - abs(amount_diff_eur) - abs(date_diff_days)*2 + (20 if counterparty matches else 0)`
- [ ] `POST /api/commitments/{id}/match` — body `{transaction_id}`. Vérifie que la tx est accessible + pas déjà liée à un autre commitment. Set `matched_transaction_id`, `status=paid`.
- [ ] `POST /api/commitments/{id}/unmatch` — reset `matched_transaction_id=NULL`, `status=pending`.
- [ ] `GET /api/commitments/{id}/suggest-matches` — appelle le service.
- [ ] Tests : match happy path, match transaction inaccessible → 403, match transaction déjà liée → 409, unmatch, suggest returns sorted candidates
- [ ] Commit : `feat(api/commitments): match/unmatch/suggest + scoring service`

### Task 1.6 : Matching auto à l'import

**Files:**
- Modify: `backend/app/services/imports.py`

- [ ] Après insertion d'une transaction, appeler `suggest_matches(session, commitment)` pour chaque commitment `pending` de la même `entity_id, direction`, mais inversement (commitments candidats pour chaque tx insérée). Si **exactement 1** suggestion avec score ≥ 80 → auto-link.
- [ ] Test d'intégration : importer un fixture Delubac contenant une tx qui matche un commitment pré-créé → vérifier l'auto-link.
- [ ] Commit : `feat(imports): auto-match pending commitments`

---

## Phase 2 — Engagements frontend

### Task 2.1 : Types + hooks API

**Files:**
- Create: `frontend/src/api/commitments.ts`

- [ ] Types `Commitment`, `CommitmentCreate`, `CommitmentUpdate` miroir des schemas backend.
- [ ] Hooks : `useCommitments({entityId, status, ...})`, `useCommitment(id)`, `useCreateCommitment()`, `useUpdateCommitment()`, `useCancelCommitment()`, `useMatchCommitment(id)`, `useUnmatchCommitment(id)`, `useSuggestMatches(id)`. Utiliser `apiFetch` depuis `@/api/client`.
- [ ] Commit : `feat(api): commitments hooks`

### Task 2.2 : `CommitmentsPage` CRUD

**Files:**
- Create: `frontend/src/pages/CommitmentsPage.tsx`
- Create: `frontend/src/pages/CommitmentFormDialog.tsx`
- Modify: `frontend/src/router.tsx` (route `/engagements`)
- Modify: `frontend/src/components/Sidebar.tsx` (item Pilotage > "Engagements")

Design : **utiliser design-taste-frontend tokens** (bg-panel, shadow-card, border-line-soft, text-ink, typo 12.5-13px) pour rester cohérent avec les autres pages.

- [ ] Page : header (h1 "Engagements" + `<EntitySelector />` + bouton "Nouveau"), table avec colonnes : Date émission, Date prévue, Tiers, Catégorie, Direction (pill vert/rouge), Montant (mono, signé), Statut (badge : en attente/payée/annulée), Actions (Éditer, Matcher si pending)
- [ ] Filtres : status (tabs), direction (radio), période (date range)
- [ ] `CommitmentFormDialog` : reprend le pattern de `AdminUsersResetPasswordDialog` (overlay + Card centrée), champs : counterparty (combobox), category (combobox), direction (radio), montant, date émission, date prévue, référence, description, fichier PDF optionnel (réutilise `FileDropzone`)
- [ ] Tests : render de la page vide (empty state), render avec liste, création via dialog
- [ ] Commit : `feat(commitments): CRUD page + form dialog + sidebar entry`

### Task 2.3 : `CommitmentMatchDialog`

**Files:**
- Create: `frontend/src/pages/CommitmentMatchDialog.tsx`

- [ ] Modale avec liste des suggestions (via `useSuggestMatches`) — chaque candidat affiche date, libellé, montant, score ; bouton "Lier" à côté.
- [ ] Option "Rechercher une autre transaction" (champ search + liste filtrée)
- [ ] Commit : `feat(commitments): match dialog with suggestions`

---

## Phase 3 — Scenarios + Lines backend

### Task 3.1 : Modèles `ForecastScenario` + `ForecastLine` + enum `ForecastMethod`

**Files:**
- Create: `backend/app/models/forecast_scenario.py`
- Create: `backend/app/models/forecast_line.py`
- Modify: `backend/app/models/__init__.py`

- [ ] Enum `ForecastMethod` avec les 8 valeurs du design
- [ ] `ForecastScenario` : id, entity_id FK, name, description, is_default, created_by_id, timestamps. Relation `lines: list[ForecastLine]`.
- [ ] `ForecastLine` : toutes les colonnes du design. Relations vers Scenario, Category, base_category. Vérifier via validator Pydantic (dans schemas, pas model) que les bons champs sont remplis selon la méthode.
- [ ] Commit : `feat(models): ForecastScenario + ForecastLine + enum`

### Task 3.2 : Schemas Pydantic + validation conditionnelle

**Files:**
- Modify: `backend/app/schemas/forecast.py`

- [ ] `ScenarioRead`, `ScenarioCreate`, `ScenarioUpdate`
- [ ] `LineRead`, `LineUpsert` (un seul schema d'upsert avec validator) :
  - `RECURRING_FIXED` → `amount_cents` requis
  - `BASED_ON_CATEGORY` → `base_category_id` + `ratio` requis
  - `FORMULA` → `formula_expr` requis
  - Autres méthodes → aucun param additionnel
  - Utiliser `model_validator(mode="after")` pour enforcer
- [ ] Tests validation : chaque méthode avec les bons champs (pass) + avec les mauvais (fail)
- [ ] Commit : `feat(schemas): forecast scenario + line payloads with conditional validation`

### Task 3.3 : Seed scénario "Principal" par défaut par entité

**Files:**
- Create: `backend/alembic/versions/<ts>_seed_default_forecast_scenarios.py` (migration data)

- [ ] Pour chaque entité existante en DB, créer un `ForecastScenario(name="Principal", is_default=True, created_by_id=(premier admin))`
- [ ] Ajouter également un hook (fonction utilitaire `ensure_default_scenario(session, entity)` appelée à la création d'entité dans `POST /api/entities` — backend/app/api/entities.py)
- [ ] Tests : créer une nouvelle entité via l'API → scénario par défaut créé ; ancien entity → scénario créé par la migration
- [ ] Commit : `feat(forecast): default scenario "Principal" per entity`

### Task 3.4 : Endpoints CRUD scenarios

**Files:**
- Create: `backend/app/api/forecast_scenarios.py`
- Modify: `backend/app/main.py` (include_router)

- [ ] `GET /api/forecast/scenarios?entity_id` — filtre entité + accessible
- [ ] `POST /api/forecast/scenarios` — si `is_default=true`, basculer les autres de l'entité à false (transaction)
- [ ] `PATCH /api/forecast/scenarios/{id}` — idem
- [ ] `DELETE /api/forecast/scenarios/{id}` — 409 si is_default=true ET c'est le seul scenario de l'entité (prévention d'un état sans default)
- [ ] Tests : switch default transactionnel (deux PATCH concurrents → pas d'incohérence), delete default seul → 409, delete default avec autres → OK + promouvoir un autre en default
- [ ] Commit : `feat(api): forecast scenarios CRUD`

### Task 3.5 : Endpoints CRUD lines + validation formule

**Files:**
- Create: `backend/app/api/forecast_lines.py`
- Modify: `backend/app/main.py` (include_router)

- [ ] `GET /api/forecast/lines?scenario_id` — filtre + accès
- [ ] `PUT /api/forecast/lines` — upsert sur (scenario_id, category_id). Si `method=FORMULA`, valider le formula_expr via `formula_parser.parse()` (lever 422 si invalide). Détecter cycle via `detect_cycle(expr, all_lines)` (impl en Phase 4).
- [ ] `DELETE /api/forecast/lines/{id}`
- [ ] `POST /api/forecast/lines/validate-formula` — body `{scenario_id, formula_expr, category_id?}` → 200 si OK, 422 avec message si invalide
- [ ] Tests : upsert crée puis met à jour ; formula invalide rejetée ; cycle rejeté
- [ ] Commit : `feat(api): forecast lines upsert + formula validation`

---

## Phase 4 — Moteur de calcul + DSL parser

### Task 4.1 : Parser DSL

**Files:**
- Create: `backend/app/services/formula_parser.py`
- Create: `backend/tests/services/test_formula_parser.py`

Grammaire (cf. design) : `expr := term (('+' | '-') term)*`, etc. Parser récursif descendant.

- [ ] **Test d'abord** — couvrir :
  - Nombres entiers + décimaux : `5`, `5.5`, `-3`
  - Refs simples : `{Ventes}`
  - Refs avec offset : `{Ventes_M-1}`, `{Salaires_M-12}`
  - Opérateurs : `+`, `-`, `*`, `/`
  - Parenthèses : `({A} + {B}) * 2`
  - Cas invalides : `{`, `{}`, `5 +`, `{A} ++`, `1 / 0` (détecté à l'évaluation pas au parse)
- [ ] Implémenter : `tokenize(expr) -> list[Token]`, `parse(tokens) -> AST` (nœuds `Num`, `Ref`, `BinOp`, `UnaryOp`), `ast_to_dict(ast)` pour sérialisation debug
- [ ] `extract_refs(ast) -> list[tuple[str, int]]` retourne les catégories référencées (pour détection cycle)
- [ ] `evaluate(ast, resolver: Callable[[str, int], Decimal]) -> Decimal` — le resolver sait lire `(category_name, month_offset) -> valeur`
- [ ] Détection cycle : fonction `detect_cycle(scenario_id, category_id, formula_expr, session) -> bool` qui BFS sur les refs
- [ ] Commit : `feat(services): formula DSL parser + evaluator`

### Task 4.2 : Moteur de calcul — méthodes simples

**Files:**
- Create: `backend/app/services/forecast_engine.py`
- Create: `backend/tests/services/test_forecast_engine.py`

- [ ] **Test d'abord** — créer un dataset fixture : entité avec 12 mois de transactions passées sur 3 catégories (Salaires -3000/mois, Ventes +5000/mois, Loyer -800/mois).
- [ ] `CellValue` dataclass : `realized_cents, committed_cents, forecast_cents, total_cents, line_method?, line_params?`
- [ ] `compute_cell(session, scenario_id, entity_id, category_id, month) -> CellValue`
- [ ] Méthodes implémentées (dans `_evaluate_line(line, context)` où context contient le mois cible + fonction résolveur) :
  - `RECURRING_FIXED` → retourne `line.amount_cents`
  - `AVG_3M`/`AVG_6M`/`AVG_12M` → moyenne des N mois précédents de **transactions (même catégorie, même entité)** (ignorer commitments pour éviter les doubles comptages)
  - `PREVIOUS_MONTH` → réalisé M-1
  - `SAME_MONTH_LAST_YEAR` → réalisé même mois Y-1
  - `BASED_ON_CATEGORY` → réalisé de `base_category_id` au mois cible × `ratio`
- [ ] Tests pour chaque méthode contre le fixture
- [ ] Commit : `feat(forecast-engine): methods — fixed/avg/previous/based_on`

### Task 4.3 : Moteur — méthode FORMULA + orchestration

**Files:**
- Modify: `backend/app/services/forecast_engine.py`
- Modify: `backend/tests/services/test_forecast_engine.py`

- [ ] Méthode `FORMULA` : résoudre les refs via le moteur (récursion protégée par `detect_cycle` en amont)
- [ ] `compute_cell` final : `realized = SUM transactions ; committed = SUM commitments pending ; forecast = (line evaluated if line else 0) + SUM(forecast_entries manuels)`. Convention mois courant : cf. design.
- [ ] Tests : combiner formule `{Ventes} * 0.2` avec les fixtures ; vérifier mois courant split (réalisé + committed + forecast_restant).
- [ ] Commit : `feat(forecast-engine): formula method + compute_cell orchestration`

### Task 4.4 : Agrégation pivot (fonction `compute_pivot`)

**Files:**
- Modify: `backend/app/services/forecast_engine.py`

- [ ] `compute_pivot(session, scenario_id, entity_id, from_month, to_month, account_ids=None) -> PivotResult`
- [ ] PivotResult : `months`, `opening_balance_cents`, `closing_balance_projection_cents (par mois)`, `rows` (hiérarchiques), `realized_series`, `forecast_series`, `totals`
- [ ] Hiérarchie : récupérer toutes les catégories accessibles avec parent, construire l'arbre ; pour chaque nœud, agréger les cells
- [ ] Opening balance : somme des `closing_balance` du dernier import complet **filtré par `account_ids`** si fourni
- [ ] Projection fin de mois : `previous + total_encaissements - total_decaissements` cumulatif
- [ ] Test : seed 2 catégories × 3 mois × 1 line → vérifier pivot retourne la bonne structure
- [ ] Commit : `feat(forecast-engine): compute_pivot aggregation`

---

## Phase 5 — Endpoint Pivot

### Task 5.1 : `GET /api/forecast/pivot`

**Files:**
- Create: `backend/app/api/forecast_pivot.py`
- Modify: `backend/app/main.py`

- [ ] Params : `scenario_id`, `entity_id`, `from=YYYY-MM`, `to=YYYY-MM`, `accounts=csv` (IDs de bank_account)
- [ ] Validation : scenario accessible, entity accessible, range ≤ 36 mois (garde-fou), accounts appartiennent à entity
- [ ] Appel `compute_pivot` + sérialisation
- [ ] Headers : `Cache-Control: private, max-age=30`
- [ ] Test E2E : GET avec fixtures → structure attendue
- [ ] Commit : `feat(api): GET /api/forecast/pivot`

### Task 5.2 : `GET /api/dashboard/month-comparison`

**Files:**
- Modify: `backend/app/api/dashboard.py`

- [ ] Param `entity_id`
- [ ] Calcul : pour mois courant + mois précédent, somme des transactions `direction=CREDIT` (in) et `direction=DEBIT` (out) sur entités accessibles
- [ ] Réponse : `{ current: {in_cents, out_cents, month_label}, previous: {in_cents, out_cents, month_label} }`
- [ ] Test + commit `feat(dashboard): month comparison endpoint`

---

## Phase 6 — Forecast v2 frontend

### Task 6.1 : Types + hooks API

**Files:**
- Create: `frontend/src/types/forecast.ts`
- Create: `frontend/src/api/forecastScenarios.ts`
- Create: `frontend/src/api/forecastLines.ts`
- Create: `frontend/src/api/forecastPivot.ts`
- Create: `frontend/src/api/dashboardComparison.ts`

- [ ] Types miroir : `Scenario`, `ForecastLine`, `ForecastMethod` (enum), `PivotResult`, `PivotCell`, `PivotRow`, `MonthComparison`
- [ ] Hooks standards : `useScenarios(entityId)`, `useCreateScenario`, `useUpdateScenario`, `useDeleteScenario`, `useLines(scenarioId)`, `useUpsertLine`, `useDeleteLine`, `useValidateFormula`, `usePivot(params)`, `useMonthComparison(entityId)`
- [ ] Commit : `feat(api): forecast v2 hooks`

### Task 6.2 : Composants orchestrateurs — ScenarioSelector + ConsolidatedAccountsPopover

**Files:**
- Create: `frontend/src/components/forecast/ScenarioSelector.tsx`
- Create: `frontend/src/components/forecast/ConsolidatedAccountsPopover.tsx`
- Create: `frontend/src/stores/forecastUi.ts` (Zustand : scenarioId actif, accountIds filtrés — pas de persistence car per-session)

- [ ] `ScenarioSelector` : composant `Select` shadcn avec liste + séparateur + items "Renommer / Dupliquer / Supprimer" ; bouton "+" pour nouveau scénario
- [ ] `ConsolidatedAccountsPopover` : `Popover` + liste de checkboxes par compte (récupère via `useBankAccounts({entityId})`) + "Tout sélectionner" / "Désélectionner" + "Valider"
- [ ] Commit : `feat(forecast): scenario selector + consolidated accounts popover + ui store`

### Task 6.3 : `PivotBars` (barres hautes + courbe solde)

**Files:**
- Create: `frontend/src/components/forecast/PivotBars.tsx`

- [ ] ComposedChart recharts. Barres par mois : encaissements (emerald) empilées haut, décaissements (rose) en bas. Partie réalisée plein, prévisionnelle hachurée (pattern SVG).
- [ ] Courbe solde superposée : ligne continue mois passés + pointillée mois futurs (2 datasets séparés).
- [ ] Tooltip custom avec valeurs fr-FR.
- [ ] Commit : `feat(forecast): PivotBars chart`

### Task 6.4 : `PivotTable` (tableau hiérarchique)

**Files:**
- Create: `frontend/src/components/forecast/PivotTable.tsx`
- Create: `frontend/src/test/forecast/PivotTable.test.tsx`

- [ ] Première colonne figée (CSS `position: sticky; left: 0`), colonnes mois scrollables horizontalement.
- [ ] Lignes :
  - Header colonnes : mois en abréviation FR (JANV. 26, etc.)
  - Ligne spéciale "Trésorerie en début de mois" (grisée)
  - Lignes Encaissements/Décaissements expandable avec chevron ; rendu récursif selon `parent_id`
  - Cells : réalisé (noir) / prévi (italique gris) ; mois courant avec barre verticale `border-l-2 border-accent`
  - Hover : `bg-panel-2/50`
  - Clic cellule future (month >= current_month) → `onCellClick(month, categoryId)` → ouvre drawer
- [ ] Cellules numériques : `font-mono tabular-nums text-right` + formatage fr-FR
- [ ] Test : render fixture 2 catégories × 6 mois, vérifier chevron expand, vérifier clic sur cell future déclenche callback
- [ ] Commit : `feat(forecast): PivotTable component`

### Task 6.5 : `MethodForm` (radio méthode + sous-options)

**Files:**
- Create: `frontend/src/components/forecast/MethodForm.tsx`

- [ ] Radio group des 8 méthodes (libellés FR : "Récurrent à montant fixe", "Moyenne 3 mois précédents", etc.)
- [ ] Conditional fields :
  - `RECURRING_FIXED` → input montant
  - `BASED_ON_CATEGORY` → select catégorie + input ratio (%)
  - `FORMULA` → textarea avec bouton "Valider la formule" (appelle `useValidateFormula`, affiche erreur inline si 422)
- [ ] Preview calculé : petit panneau à droite qui appelle `usePivot` avec un scenario temporaire pour montrer la valeur résultante. **Simplification pour v1 :** preview = "(à jour après enregistrement)" si la logique de preview live est complexe ; laisser à v2.
- [ ] Commit : `feat(forecast): MethodForm with conditional fields`

### Task 6.6 : `CellEditorDrawer` (3 onglets)

**Files:**
- Create: `frontend/src/components/forecast/CellEditorDrawer.tsx`
- Create: `frontend/src/test/forecast/CellEditorDrawer.test.tsx`

- [ ] Overlay + panel droit largeur 420px (pas de composant shadcn `Sheet` existant ; implémenter en fixed + transition `translate-x-full → translate-x-0`)
- [ ] Header : mois + catégorie + bouton close
- [ ] Tabs : "Payées", "Engagées", "Prévisionnel"
  - Payées : fetch `useTransactions({entityId, categoryId, dateFrom, dateTo})` puis liste
  - Engagées : fetch `useCommitments({entityId, categoryId, from, to, status:"pending"})` puis liste
  - Prévisionnel : `<MethodForm>` pré-rempli avec la line actuelle (via `useLines`) + bouton "Enregistrer" → `useUpsertLine`
- [ ] Fermeture : ESC, clic overlay, bouton close
- [ ] Test : onglets navigables, méthode change met à jour le form, save déclenche mutation
- [ ] Commit : `feat(forecast): CellEditorDrawer with 3 tabs`

### Task 6.7 : Page `/previsionnel` v2

**Files:**
- Create: `frontend/src/pages/ForecastV2Page.tsx`
- Delete: `frontend/src/pages/ForecastPage.tsx` (après migration)
- Modify: `frontend/src/router.tsx` (remplacer import)

- [ ] Header : h1 + `<EntitySelector />` + `<ScenarioSelector />` + `<ConsolidatedAccountsPopover />` + bouton "Rafraîchir"
- [ ] Contenu : `<PivotBars />` puis `<PivotTable />`
- [ ] State : `const [editingCell, setEditingCell] = useState<{month, categoryId}|null>(null)` ; passer à `CellEditorDrawer open={editingCell!==null}`
- [ ] Empty state : si aucun scénario, message "Créez votre premier scénario pour démarrer"
- [ ] Remplacer l'ancienne `ForecastPage.tsx` dans le router
- [ ] Commit : `feat(forecast): v2 page replacing v1`

---

## Phase 7 — Dashboard comparison widget

### Task 7.1 : `MonthComparisonCard`

**Files:**
- Create: `frontend/src/components/dashboard/MonthComparisonCard.tsx`
- Modify: `frontend/src/pages/DashboardPage.tsx`

- [ ] Card avec titre "Réalisé mois en cours vs mois précédent", BarChart recharts à 2 groupes (Encaissements / Décaissements) × 2 séries (mois courant / précédent)
- [ ] Couleurs : emerald/rose mais patterns différents pour distinguer les 2 mois (plein vs hachures, cf. image 4)
- [ ] Insérer dans DashboardPage après les KPI cards, avant les BankBalancesSection
- [ ] Commit : `feat(dashboard): month comparison widget`

---

## Phase 8 — E2E + merge + deploy

### Task 8.1 : Vérifications finales

- [ ] Backend : `cd backend && uv run pytest tests/ -q 2>&1 | tail -10` → tout passe
- [ ] Frontend : `cd frontend && pnpm run test -- --run 2>&1 | tail -10` → tout passe
- [ ] Frontend build : `cd frontend && pnpm run build` → OK
- [ ] Smoke manuel local si possible (sinon en prod après déploiement)

### Task 8.2 : Merge + tag + rebuild prod

- [ ] `git checkout main && git merge --no-ff plan-5b-forecast-v2 -m "merge: plan-5b — forecast v2 agicap-like"`
- [ ] `git tag plan-5b-done`
- [ ] `git push origin main --tags`
- [ ] `docker compose -f docker-compose.prod.yml up -d --build`
- [ ] Vérifier `curl https://horizon.acreedconsulting.com/readyz` = 200
- [ ] Test manuel en prod :
  - [ ] Créer un commitment via `/engagements`
  - [ ] Ouvrir `/previsionnel` → pivot charge, barres affichent, courbe solde visible
  - [ ] Cliquer sur cellule future → drawer s'ouvre, 3 onglets navigables
  - [ ] Choisir méthode AVG_3M sur catégorie Salaires, enregistrer → pivot se recalcule
  - [ ] Changer de scénario → pivot change
  - [ ] Toggle comptes consolidés → pivot change
  - [ ] Dashboard affiche widget comparison

---

## Self-Review

**Spec coverage :**
- Engagements module (CRUD + match + auto-import) → Tasks 1.1–1.6, 2.1–2.3 ✅
- Scenarios + default per entity → Tasks 3.1, 3.3, 3.4 ✅
- ForecastLine + 8 méthodes → Tasks 3.1, 3.2, 3.5, 4.1–4.3 ✅
- Formule DSL → Task 4.1 ✅
- Pivot endpoint + hiérarchie + vue consolidée comptes → Tasks 4.4, 5.1 ✅
- Page Forecast v2 + drawer cellule → Tasks 6.1–6.7 ✅
- Widget dashboard comparison → Tasks 5.2, 7.1 ✅
- Design via design-taste-frontend/gpt-taste → mentionné dans 2.2, 6.3–6.7 (tokens existants + pas de card overuse + mono tabular pour les chiffres)

**Placeholder scan :** "Preview live calculé" en Task 6.5 est marqué comme simplifié pour v1 — c'est une décision YAGNI explicite, pas un TBD.

**Type consistency :** `amount_cents` partout (Commitment + ForecastLine). `ForecastMethod` enum cohérent. `PivotCell` avec `realized_cents, committed_cents, forecast_cents, total_cents` aligné entre backend et frontend. `month` toujours au format `YYYY-MM` string ou `date` 1er du mois.

**Note d'exécution :** Phase ≠ Task pour subagent-driven-development ; dispatcher un subagent par **Phase complète** vu que les tâches d'une phase sont tightly coupled (mêmes fichiers touchés). 8 phases ≈ 8 subagents.
