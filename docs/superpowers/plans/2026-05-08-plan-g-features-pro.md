# Plan G — Features pro — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** Ajouter les 12 fonctionnalités qui distinguent Horizon d'une démo et le positionnent en outil pro. Couverture : graphe de solde quotidien (G1), rolling 13-week (G2), bandeau DSO/DPO/BFR sur Forecast (G3), anomalies p95 (G4), 2FA TOTP (G5 — déféré, voir arbitrage), forgot-password (G6 — déféré, voir arbitrage), overlay multi-scénarios (G7), what-if sans persistence (G8), saisonnalité (G9), position par compte bancaire (G10), export CSV/XLSX (G11), snooze/acquittement de dérive (G12).

**Architecture :**
- Backend (Python/FastAPI/SQLAlchemy 2.x) : 2 nouvelles migrations (G12 : table `drift_acks`), 5 nouveaux endpoints dans les routers existants (`analysis.py`, `dashboard.py`, `forecast.py`), 2 nouveaux modules de service (`services/anomaly.py`, extension de `services/analysis.py`), et les streams CSV/XLSX en réponses de streaming `StreamingResponse`.
- Frontend (React 18 / TS / react-query / Tailwind / Recharts) : 8 nouveaux composants, modifications de `DashboardPage`, `ForecastV2Page`, `AnalysePage`, `PivotTable`, `CategoryDriftTable`, `router.tsx`, `documentation.ts`.
- Tests : pytest dans le container (`docker exec horizon-backend-1 pytest tests/`), Vitest pour le frontend (`cd frontend && npx vitest --run`).
- Documentation d'impact (CLAUDE.md) : G1, G2, G3, G4, G7, G8, G9, G10, G11, G12 → `documentation.ts` obligatoire.

**Tech Stack :** FastAPI, SQLAlchemy 2.x, Postgres, Alembic, React 18, react-query 5, react-router-dom 6, TypeScript, Tailwind, Recharts 3.x, pytest, Vitest. XLSX via `openpyxl` si disponible dans le container (vérifier G11).

---

## Vérifications préalables — Résultats d'exploration

### 1. pyotp (G5)

`pyotp` n'est **pas** dans `backend/pyproject.toml`. Absent de l'image prod. **G5 déféré → Plan H.**

### 2. SMTP / email (G6)

`grep -rn "SMTP\|MAIL" backend/app/ backend/pyproject.toml` retourne uniquement `email-validator` (validation de format) et des occurrences dans `models/user.py`, `schemas/user.py` (champ `email`). Aucune infra d'envoi SMTP (pas de `aiosmtplib`, `fastapi-mail`, `resend`, ni de template email). **G6 déféré → Plan H.**

### 3. compute_working_capital (G3)

Signature confirmée : `compute_working_capital(session: Session, *, entity_id: int) -> WorkingCapitalResponse` dans `backend/app/services/analysis.py:921`. Endpoint `/api/analysis/working-capital` déjà exposé dans `backend/app/api/analysis.py:122`. Hook `useWorkingCapital` déjà présent dans `frontend/src/api/analysis.ts:237`. **G3 = branchement UI uniquement, aucun changement backend.**

### 4. Recharts (G1, G2, G9, G10)

Confirmé : `"recharts": "^3.8.1"` dans `frontend/package.json`. Composants `AreaChart`, `Area`, `BarChart`, `Bar`, `XAxis`, `YAxis`, `Tooltip`, `ResponsiveContainer` déjà importés dans `DashboardPage.tsx`. Réutiliser sans import supplémentaire.

### 5. closing_balance (G1, G10)

Confirmé : `closing_balance: Mapped[Optional[Decimal]]` dans `backend/app/models/import_record.py:46`. La fonction `_compute_total_balance` dans `dashboard.py:320` calcule déjà le Σ closing_balance par compte. La fonction `_compute_balance_trend` reconstruit le solde quotidien sur N jours. **G1 réutilise ces helpers en les exposant dans un nouvel endpoint dédié.**

### 6. ForecastV2Page (G7, G3)

`frontend/src/pages/ForecastV2Page.tsx` : header avec `EntitySelector`, `ScenarioSelector`, `ConsolidatedAccountsPopover`, `PeriodSelector`. Corps : `PivotBars` + `PivotTable`. L'état `scenarioId` vient du store `useForecastUi`. G3 ajoute un bandeau KPI entre le header et `PivotBars`. G7 ajoute un sélecteur de scénario de comparaison + overlay sur `PivotBars`.

### 7. Migration head actuelle

Dernière migration en date : `20260507_2020_e5_client_error_acknowledged.py`. Les révisions G seront préfixées `20260507_g{n}00_...`.

### 8. openpyxl (G11)

À vérifier au moment de G11 : `docker exec horizon-backend-1 pip show openpyxl 2>&1`. Si présent → export XLSX en bonus. Si absent → CSV uniquement (pas de blocage, pas d'ajout de dépendance non validée).

---

## File Structure

### Création

**Backend**

- `backend/alembic/versions/20260507_g1200_drift_acks.py` — table `drift_acks` + index. Révision `h0r1z0ng1200`.
- `backend/app/services/anomaly.py` — `detect_anomalies(session, *, entity_id, days=180)`.
- `backend/app/schemas/treasury.py` — schémas `DailyBalancePoint`, `DailyBalanceResponse`, `PerAccountBalance`, `PerAccountBalanceResponse`, `Rolling13WPoint`, `Rolling13WResponse`.
- `backend/app/schemas/anomaly.py` — `AnomalyRow`, `AnomalyResponse`.
- `backend/app/schemas/drift_ack.py` — `DriftAckCreate`, `DriftAckRead`, `DriftSnoozeRequest`.
- `backend/app/models/drift_ack.py` — modèle SQLAlchemy `DriftAck`.
- `backend/app/api/treasury.py` — router `/api/treasury` : endpoints G1 (`/daily-balance`), G10 (`/per-account`).
- `backend/app/api/anomaly.py` — router `/api/analysis/anomalies` (G4).
- `backend/app/api/drift_acks.py` — router `/api/analysis/drift-acks` (G12).
- `backend/tests/test_g1_daily_balance.py`
- `backend/tests/test_g2_rolling13w.py`
- `backend/tests/test_g4_anomalies.py`
- `backend/tests/test_g9_seasonality.py`
- `backend/tests/test_g10_per_account.py`
- `backend/tests/test_g11_exports.py`
- `backend/tests/test_g12_drift_acks.py`

**Frontend**

- `frontend/src/components/treasury/DailyBalanceChart.tsx` — AreaChart Recharts (G1).
- `frontend/src/components/treasury/PerAccountWidget.tsx` — carte par compte bancaire avec sparkline (G10).
- `frontend/src/components/forecast/WorkingCapitalBanner.tsx` — bandeau 3 KPI DSO/DPO/BFR (G3).
- `frontend/src/components/forecast/ScenarioOverlay.tsx` — overlay 2e scénario sur PivotBars (G7).
- `frontend/src/components/analyse/AnomalyCard.tsx` — carte anomalies p95 (G4).
- `frontend/src/components/analyse/SeasonalityCard.tsx` — graphe saisonnalité catégorie × mois (G9).
- `frontend/src/api/treasury.ts` — fetchers + hooks G1, G10.
- `frontend/src/api/anomaly.ts` — fetcher + hook G4.
- `frontend/src/api/seasonality.ts` — fetcher + hook G9.
- `frontend/src/api/driftAcks.ts` — fetchers + hooks G12.
- `frontend/src/api/exports.ts` — fetcher générique `downloadCsv(url, filename)` + exports par page (G11).

### Modification

**Backend**

- `backend/app/api/router.py` — ajouter `treasury`, `anomaly`, `drift_acks`.
- `backend/app/api/analysis.py` — ajouter endpoint `GET /api/analysis/seasonality` (G9).
- `backend/app/api/forecast.py` — ajouter endpoint `GET /api/forecast/rolling-13w` (G2).
- `backend/app/api/transactions.py` — ajouter endpoint `GET /api/transactions/export` (G11 transactions).
- `backend/app/api/admin_audit.py` — ajouter endpoint `GET /api/admin/audit/export` (G11 audit).
- `backend/app/api/analysis.py` — ajouter endpoints `GET /api/analysis/drift/export`, `GET /api/analysis/top-movers/export`, `GET /api/analysis/yoy/export`, `GET /api/analysis/runway/export` (G11 analyse).
- `backend/app/api/forecast_pivot.py` — ajouter endpoint `GET /api/forecast/pivot/export` (G11 pivot).
- `backend/app/services/analysis.py` — ajouter `compute_seasonality(...)` et `compute_category_drift` modifié pour lire `DriftAck` (G9, G12).
- `backend/app/models/__init__.py` — ajouter `DriftAck`.

**Frontend**

- `frontend/src/pages/DashboardPage.tsx` — ajouter `DailyBalanceChart` en haut de page + `PerAccountWidget` dans la section soldes (G1, G10).
- `frontend/src/pages/ForecastV2Page.tsx` — ajouter `WorkingCapitalBanner` entre header et `PivotBars` ; ajouter `ScenarioOverlay` avec sélecteur de scénario de comparaison (G3, G7).
- `frontend/src/pages/AnalysePage.tsx` — ajouter `AnomalyCard` + `SeasonalityCard` dans la grille (G4, G9).
- `frontend/src/components/forecast/PivotTable.tsx` — ajouter état `overrides: Map<string, number>` + colonne override + bouton "Réinitialiser" (G8).
- `frontend/src/components/analyse/CategoryDriftTable.tsx` — ajouter bouton "Snooze 30 j" par ligne `status=alert`, appel `POST /api/analysis/drift-acks` (G12).
- `frontend/src/content/documentation.ts` — nouvelles `FeatureDoc` pour G1, G2, G3, G4, G7, G8, G9, G10, G11, G12.

---

## Conventions

- **Commits** : `feat(scope): message (G{n})`, sans emoji, en français sobre. Co-author : `Co-authored-by: Claude <claude@anthropic.com>`.
- **Montants** : toujours en centimes (`int`) dans les schemas backend. Conversion en euros côté frontend uniquement.
- **Multi-tenant** : tout endpoint qui prend `entity_id` doit appeler `require_entity_access(session=session, user=user, entity_id=entity_id)` avant tout calcul.
- **Tests** : chaque endpoint a au moins un test dans `backend/tests/test_g{n}_*.py`. Pattern : fixture `test_user` + `test_client`, authentification via cookie de session.
- **HelpTooltip** : le projet n'a pas de composant `HelpTooltip` dédié. Utiliser un `<span title="...">` sur un bouton `?` inline avec la classe `text-muted-foreground text-[11px] cursor-help` pour rester cohérent avec `CategoryDriftTable`.
- **Placeholder données insuffisantes (G9)** : si l'endpoint renvoie moins de 13 mois de données, afficher un encadré `bg-amber-50 text-amber-900 rounded-md px-4 py-3 text-[13px]` avec le message "Données insuffisantes pour afficher la saisonnalité (X mois disponibles sur 13 nécessaires). Ce graphique sera utile à partir de [date estimée]."

---

## Task G1 — Solde de trésorerie quotidien sur 90 jours

**Pourquoi :** Le graphe central d'Agicap. Donne une vue immédiate de la position de trésorerie dans le temps et des tendances. Actuellement, `DashboardPage` a un graphe "Solde estimé" reconstruit à rebours — G1 l'expose comme endpoint dédié avec paramétrage `entity_id` + `days`.

**Files :**
- `backend/app/schemas/treasury.py` (créer)
- `backend/app/api/treasury.py` (créer)
- `backend/app/api/router.py` (modifier)
- `backend/tests/test_g1_daily_balance.py` (créer)
- `frontend/src/api/treasury.ts` (créer)
- `frontend/src/components/treasury/DailyBalanceChart.tsx` (créer)
- `frontend/src/pages/DashboardPage.tsx` (modifier)
- `frontend/src/content/documentation.ts` (modifier)

**Steps :**

- [ ] **Backend — Schéma** : créer `backend/app/schemas/treasury.py` avec :
  ```python
  from pydantic import BaseModel
  from datetime import date
  from decimal import Decimal

  class DailyBalancePoint(BaseModel):
      date: date
      balance: Decimal

  class DailyBalanceResponse(BaseModel):
      entity_id: int
      days: int
      points: list[DailyBalancePoint]
      latest_balance: Decimal | None
      latest_date: date | None
  ```

- [ ] **Backend — Endpoint** : créer `backend/app/api/treasury.py`. Endpoint `GET /api/treasury/daily-balance`. Réutiliser `_compute_total_balance` et `_compute_balance_trend` de `dashboard.py` en les déplaçant (ou en important) dans un helper partagé. Logique : résoudre les comptes bancaires accessibles pour l'entité (pattern identique à `_resolve_accessible_bank_accounts` dans `dashboard.py`), calculer `total_balance` et `last_date` via le Σ `closing_balance`, puis appeler `_compute_balance_trend`. Si aucun compte ou aucune donnée : retourner `points=[]`, `latest_balance=None`, `latest_date=None`.
  ```python
  @router.get("/daily-balance", response_model=DailyBalanceResponse)
  def get_daily_balance(
      entity_id: int = Query(...),
      days: int = Query(90, ge=7, le=365),
      user: User = Depends(get_current_user),
      db: Session = Depends(get_db),
  ) -> DailyBalanceResponse:
      require_entity_access(session=db, user=user, entity_id=entity_id)
      ...
  ```

- [ ] **Backend — Router** : dans `backend/app/api/router.py`, ajouter `from app.api import treasury` et `api_router.include_router(treasury.router)`.

- [ ] **Backend — Tests** : `backend/tests/test_g1_daily_balance.py`. Cas : entité sans import → `points=[]`. Entité avec imports → liste de 90 points triés par date croissante, `latest_balance` non nul, accès refusé si entité inconnue (403/422).

- [ ] **Frontend — API** : créer `frontend/src/api/treasury.ts` avec `fetchDailyBalance(args: { entityId: number; days?: number })` et hook `useDailyBalance`.

- [ ] **Frontend — Composant** : créer `frontend/src/components/treasury/DailyBalanceChart.tsx`. AreaChart Recharts avec :
  - `<ResponsiveContainer width="100%" height={220}>`
  - `<AreaChart data={points}>`
  - Aire verte (`fill="#dcfce7"`, `stroke="#16a34a"`) si dernier solde positif, rouge (`fill="#fee2e2"`, `stroke="#dc2626"`) si négatif.
  - `<XAxis dataKey="date" tickFormatter={d => DATE.format(new Date(d))} interval="preserveStartEnd" />`
  - `<YAxis tickFormatter={v => formatEUR(v)} width={90} />`
  - `<Tooltip formatter={(v) => formatEUR(Number(v))} labelFormatter={d => DATE.format(new Date(d))} />`
  - `<ReferenceLine y={0} stroke="#94a3b8" strokeDasharray="4 2" />`
  - État vide si `points.length === 0` : encadré "Aucun import disponible pour calculer l'historique de solde."
  - Skeleton `animate-pulse` pendant le chargement.

- [ ] **Frontend — DashboardPage** : insérer `<DailyBalanceChart entityId={entityId} />` en tête de la section principale, avant les KPI cards. Ajouter tooltip "?" inline : `title="Solde de trésorerie reconstruit jour par jour sur 90 jours à partir du dernier relevé importé."`.

- [ ] **Documentation** : ajouter une entrée `FeatureDoc` avec `id: "daily-balance-chart"` dans `documentation.ts`. Sections : "À quoi ça sert" = visualiser l'évolution du solde cumulé sur 90 jours ; "Ce que ça change quand tu cliques" = aucun effet (lecture seule, tooltip au survol) ; "Ce que ça ne change pas" = les transactions ni les imports ; "Quand l'utiliser" = détecter des creux de trésorerie, repérer la saisonnalité des flux, préparer un rendez-vous banquier.

- [ ] **Run tests** : `docker exec horizon-backend-1 pytest tests/test_g1_daily_balance.py -v` vert.

---

## Task G2 — Rolling 13-week côté Forecast

**Pourquoi :** La vue hebdomadaire court terme est la dimension opérationnelle d'Agicap. Mensuel = stratégique, hebdomadaire = gestion de tréso J-à-J. Permet de voir d'un coup d'œil si la semaine prochaine est tendue.

**Files :**
- `backend/app/schemas/treasury.py` (modifier — ajouter schémas 13W)
- `backend/app/api/forecast.py` (modifier — ajouter endpoint)
- `backend/tests/test_g2_rolling13w.py` (créer)
- `frontend/src/api/treasury.ts` (modifier — ajouter fetcher 13W)
- `frontend/src/components/forecast/Rolling13WChart.tsx` (créer)
- `frontend/src/pages/ForecastV2Page.tsx` (modifier — ajouter section)
- `frontend/src/content/documentation.ts` (modifier)

**Steps :**

- [ ] **Backend — Schéma** : ajouter dans `backend/app/schemas/treasury.py` :
  ```python
  class Rolling13WPoint(BaseModel):
      week_label: str        # "2026-W18"
      week_start: date       # lundi de la semaine
      realized_cents: int    # Σ transactions réalisées (négatif = débit net)
      forecast_cents: int    # Σ forecast_lines (montants en centimes)
      is_past: bool          # True si week_start < today
  
  class Rolling13WResponse(BaseModel):
      entity_id: int
      scenario_id: int | None
      points: list[Rolling13WPoint]  # 13 points : W-1 à W+11
  ```

- [ ] **Backend — Endpoint** : ajouter dans `backend/app/api/forecast.py` l'endpoint `GET /api/forecast/rolling-13w`. Logique :
  - `today = date.today()`, calculer `monday_this_week = today - timedelta(days=today.weekday())`.
  - Fenêtre : W-1 (semaine précédente, lundi) à W+11 (12 semaines dans le futur), soit 13 semaines.
  - Pour chaque semaine : `realized_cents` = `SELECT SUM(amount) FROM transactions WHERE bank_account_id IN (...) AND operation_date BETWEEN week_start AND week_end AND is_aggregation_parent = FALSE` converti en centimes.
  - `forecast_cents` = `SELECT SUM(amount_cents) FROM forecast_lines WHERE scenario_id = ? AND category_id IN (...)` agrégé par semaine de `expected_date`. Si `scenario_id` est `None`, retourner `forecast_cents=0`.
  - `week_label` = format ISO `f"{week_start.isocalendar().year}-W{week_start.isocalendar().week:02d}"`.
  - Garde-fous : `require_entity_access`, résolution des bank_account_ids identique aux autres endpoints.

- [ ] **Backend — Tests** : `backend/tests/test_g2_rolling13w.py`. Vérifier : 13 points retournés, `is_past=True` pour W-1, `is_past=False` pour W+1, accès refusé si entité étrangère.

- [ ] **Frontend — API** : ajouter `fetchRolling13W` et `useRolling13W` dans `frontend/src/api/treasury.ts`.

- [ ] **Frontend — Composant** : créer `frontend/src/components/forecast/Rolling13WChart.tsx`. `BarChart` Recharts avec barres groupées : barre verte pour `realized_cents`, barre bleue en hachures pour `forecast_cents`. Les semaines passées (`is_past=true`) ont une opacité 70%. `XAxis` = `week_label`. `YAxis` en euros. `Tooltip` formaté. Titre du composant : "Trésorerie hebdomadaire — 13 semaines glissantes (W-1 à W+11)". Tooltip "?" : `title="Vue semaine par semaine : encaissements et décaissements réalisés (semaines passées) et prévus (semaines futures)."`.

- [ ] **Frontend — ForecastV2Page** : ajouter en bas de page (après `PivotTable`) la section Rolling13W dans une carte `rounded-xl border border-line-soft bg-panel p-4 shadow-card`. Conditionner sur `effectiveEntityId != null`.

- [ ] **Documentation** : ajouter `FeatureDoc` `id: "rolling-13w"` dans `documentation.ts`.

- [ ] **Run tests** : `docker exec horizon-backend-1 pytest tests/test_g2_rolling13w.py -v` vert.

---

## Task G3 — DSO/DPO/BFR en bandeau Forecast

**Pourquoi :** Les KPI de besoin en fonds de roulement sont aujourd'hui enfermés dans `AnalysePage`. Les mettre en tête de `ForecastV2Page` ancre le prévisionnel dans la réalité des créances/dettes courantes. Aucun changement backend.

**Files :**
- `frontend/src/components/forecast/WorkingCapitalBanner.tsx` (créer)
- `frontend/src/pages/ForecastV2Page.tsx` (modifier)
- `frontend/src/content/documentation.ts` (modifier)

**Steps :**

- [ ] **Frontend — Composant** : créer `frontend/src/components/forecast/WorkingCapitalBanner.tsx`. Utilise le hook existant `useWorkingCapital({ entityId })` importé de `@/api/analysis`. Afficher 3 cartes inline :
  - DSO : `{dso_days !== null ? dso_days + " j" : "—"}` label "DSO — Délai client moyen" + tooltip `title="Nombre de jours moyen entre l'émission d'une facture client et son encaissement effectif."`.
  - DPO : `{dpo_days !== null ? dpo_days + " j" : "—"}` label "DPO — Délai fournisseur moyen" + tooltip `title="Nombre de jours moyen entre la réception d'une facture fournisseur et son règlement."`.
  - BFR : `formatCents(bfr_cents)` label "BFR — Besoin en fonds de roulement" + tooltip `title="Créances clients non encaissées moins dettes fournisseurs non réglées. Positif = vous financez vos clients."`.
  - Si `has_data=false` : encadré ambre "Aucun engagement enregistré. Ajoutez des engagements (page Engagements) pour calculer DSO, DPO et BFR."
  - Skeleton 3 cartes pendant `isLoading`.

- [ ] **Frontend — ForecastV2Page** : importer `WorkingCapitalBanner` et l'insérer entre le header et `PivotBars`, conditionné sur `effectiveEntityId != null && !noScenario`.

- [ ] **Documentation** : ajouter `FeatureDoc` `id: "working-capital-banner-forecast"` dans `documentation.ts`. "Ce que ça ne change pas" = les engagements ni le scénario de prévision — c'est une lecture seule.

---

## Task G4 — Anomalies p95 par catégorie

**Pourquoi :** Identifier automatiquement les transactions inhabituelles (montant > p95 historique de la catégorie) sans que l'utilisateur doive manuellement trier ou filtrer.

**Files :**
- `backend/app/services/anomaly.py` (créer)
- `backend/app/schemas/anomaly.py` (créer)
- `backend/app/api/anomaly.py` (créer)
- `backend/app/api/router.py` (modifier)
- `backend/tests/test_g4_anomalies.py` (créer)
- `frontend/src/api/anomaly.ts` (créer)
- `frontend/src/components/analyse/AnomalyCard.tsx` (créer)
- `frontend/src/pages/AnalysePage.tsx` (modifier)
- `frontend/src/content/documentation.ts` (modifier)

**Steps :**

- [ ] **Backend — Schéma** : créer `backend/app/schemas/anomaly.py` :
  ```python
  from pydantic import BaseModel
  from datetime import date

  class AnomalyRow(BaseModel):
      transaction_id: int
      operation_date: date
      label: str
      amount_cents: int
      category_id: int | None
      category_label: str | None
      p95_cents: int  # seuil p95 de la catégorie sur les 180 jours analysés
      ratio: float    # abs(amount) / p95, ex: 2.3 = 2.3× le p95

  class AnomalyResponse(BaseModel):
      entity_id: int
      days_analyzed: int
      anomaly_count: int
      rows: list[AnomalyRow]  # triées ratio desc
  ```

- [ ] **Backend — Service** : créer `backend/app/services/anomaly.py` avec `detect_anomalies(session, *, entity_id: int, days: int = 180) -> AnomalyResponse`. Logique SQL :
  - Récupérer toutes les transactions de l'entité sur `days` jours, exclure `is_aggregation_parent=True`.
  - Calculer par `category_id` le percentile 95 du montant absolu : utiliser `func.percentile_cont(0.95).within_group(func.abs(Transaction.amount))` (PostgreSQL). Si une catégorie a moins de 5 transactions, la sauter (pas assez de données pour p95 fiable).
  - Joindre sur `Category.name` pour le label.
  - Flaguer les transactions dont `abs(amount) > p95` calculé. Ordonner par ratio desc.
  - Limiter à 50 anomalies max retournées.

- [ ] **Backend — Endpoint** : créer `backend/app/api/anomaly.py` :
  ```python
  @router.get("/api/analysis/anomalies", response_model=AnomalyResponse)
  def get_anomalies(
      entity_id: int = Query(...),
      days: int = Query(180, ge=30, le=730),
      user: User = Depends(get_current_user),
      db: Session = Depends(get_db),
  ) -> AnomalyResponse:
      require_entity_access(session=db, user=user, entity_id=entity_id)
      return detect_anomalies(db, entity_id=entity_id, days=days)
  ```

- [ ] **Backend — Router** : ajouter `from app.api import anomaly` et `api_router.include_router(anomaly.router)` dans `router.py`.

- [ ] **Backend — Tests** : `backend/tests/test_g4_anomalies.py`. Injecter des transactions fictives, vérifier que la transaction à montant × 10 le p95 apparaît dans les anomalies. Vérifier que les catégories avec < 5 transactions sont ignorées.

- [ ] **Frontend — API** : créer `frontend/src/api/anomaly.ts` avec `fetchAnomalies`, `useAnomalies`.

- [ ] **Frontend — Composant** : créer `frontend/src/components/analyse/AnomalyCard.tsx`. Table des anomalies : colonnes Date, Libellé, Catégorie, Montant, Ratio (ex: "× 2.3"). Tri par ratio desc (déjà fait côté backend). Afficher les 10 premières + bouton "Voir les N anomalies". État vide si `anomaly_count=0` : "Aucune transaction inhabituelle détectée sur les 180 derniers jours." Tooltip "?" sur le titre : `title="Une anomalie est une transaction dont le montant absolu dépasse le 95e percentile historique de sa catégorie sur 180 jours."`.

- [ ] **Frontend — AnalysePage** : ajouter `<AnomalyCard entityId={entityId ?? undefined} />` dans la grille, en ligne 3 (col-span-12), après `CategoryDriftTable` et avant `TopMoversCard`.

- [ ] **Documentation** : `FeatureDoc` `id: "anomaly-detection"`. "Ce que ça ne change pas" = les transactions elles-mêmes ne sont pas modifiées, pas de re-catégorisation automatique.

- [ ] **Run tests** : `docker exec horizon-backend-1 pytest tests/test_g4_anomalies.py -v` vert.

---

## Task G5 — 2FA TOTP

**DEFERRED — Plan H.**

**Raison :** `pyotp` absent de `backend/pyproject.toml` et du container prod. L'ajout d'une dépendance non testée en prod requiert un rebuild de l'image Docker et une validation explicite de la compatibilité avec `argon2-cffi` et `itsdangerous`. De plus, le flow UX (QR code, codes de récupération, modification du login flow) constitue un risque de régresser l'authentification en prod sans couverture de test bout-en-bout adéquate.

**Scope Plan H :**
- Ajouter `pyotp>=2.9` dans `pyproject.toml`.
- Migration : colonne `totp_secret: str | None` sur `users`, colonne `totp_recovery_codes: JSONB | None`.
- Endpoint `POST /api/me/2fa/enroll` → génère secret, retourne URL `otpauth://` + QR en base64.
- Endpoint `POST /api/me/2fa/confirm` → valide code TOTP, active 2FA.
- Endpoint `POST /api/me/2fa/disable` → désactive.
- Modification `POST /api/auth/login` : si `totp_secret` présent, retourner `{"status": "totp_required", "partial_token": "..."}` au lieu du cookie de session ; endpoint `POST /api/auth/totp-verify` pour valider le code et émettre le cookie.
- Frontend : page `/profil` section "Authentification à deux facteurs" avec QR code (`<img src={qrDataUrl} />`), champ de saisie du code, état activé/désactivé.
- Tests complets bout-en-bout.

---

## Task G6 — Forgot-password + reset par email

**DEFERRED — Plan H.**

**Raison :** Horizon n'a aucune infrastructure SMTP configurée (pas de `aiosmtplib`, `fastapi-mail`, `resend` dans `pyproject.toml`, pas de variable `SMTP_HOST` documentée dans `backend/.env.example`). L'envoi d'un email de réinitialisation est le prérequis incontournable : implémenter le flow sans réel envoi d'email (lien token loggué en console) serait une fausse sécurité et confuserait les utilisateurs.

**Scope Plan H :**
- Arbitrage provider : Resend (API REST, pas de config SMTP, SDK Python `resend>=1.0`) ou MailJet.
- Migration : table `password_reset_tokens(id, user_id FK, token_hash, created_at, used_at)`.
- Endpoint `POST /api/auth/forgot-password` : génère `TimestampSigner(secret_key).sign(user_id)`, hash le token, stocke en DB, envoie l'email.
- Endpoint `POST /api/auth/reset-password` : vérifie la signature + expiration 1h + `used_at IS NULL`, update `password_hash`, marque le token utilisé, révoque les sessions (`session_token_version += 1`).
- Frontend : page `/mot-de-passe-oublie` (formulaire email), page `/reinitialiser-mot-de-passe?token=...` (formulaire nouveau mot de passe).
- Template email HTML simple (logo + lien + expiration).
- Tests avec mock SMTP.

---

## Task G7 — Comparaison overlay multi-scénarios

**Pourquoi :** Comparer deux scénarios (optimiste vs. pessimiste) visuellement sans quitter la page. Backend inchangé — les deux scénarios existent déjà en DB.

**Files :**
- `frontend/src/components/forecast/ScenarioOverlay.tsx` (créer)
- `frontend/src/pages/ForecastV2Page.tsx` (modifier)
- `frontend/src/content/documentation.ts` (modifier)

**Steps :**

- [ ] **Frontend — Composant ScenarioOverlay** : créer `frontend/src/components/forecast/ScenarioOverlay.tsx`. C'est un sélecteur + overlay léger :
  - Un `<select>` ou `<Combobox>` qui liste les scénarios disponibles pour l'entité (hook `useScenarios(entityId)` existant) à l'exclusion du scénario courant.
  - Quand un scénario est sélectionné, appel `usePivot({ scenarioId: overlayScenarioId, entityId, from, to, accountIds })`.
  - Retourne `{ overlayScenarioId, setOverlayScenarioId, overlayPivot }` comme hook custom `useScenarioOverlay`.

- [ ] **Frontend — Modifier PivotBars** : `frontend/src/components/forecast/PivotBars.tsx` — ajouter une prop optionnelle `overlayResult?: PivotResult`. Si présente, ajouter une 3e ligne dans le BarChart pour le solde projeté du scénario de comparaison : `<Line type="monotone" dataKey="overlay_balance" stroke="#f59e0b" strokeDasharray="6 3" strokeWidth={1.5} dot={false} name="Scénario comparaison" />`. Semi-transparent (opacité 0.6) pour distinguer du scénario principal.

- [ ] **Frontend — ForecastV2Page** : ajouter dans le header un bouton "Comparer" toggle qui, si activé, affiche le sélecteur de scénario overlay. Passer `overlayResult` à `PivotBars`. Tooltip "?" sur le bouton : `title="Superpose les flux d'un second scénario sur le graphique pour visualiser l'écart entre deux hypothèses."`.

- [ ] **Documentation** : `FeatureDoc` `id: "scenario-overlay"`. "Ce que ça ne change pas" = aucun scénario n'est modifié, c'est une visualisation en lecture seule.

---

## Task G8 — What-if sur ligne unique sans dupliquer scénario

**Pourquoi :** Permettre à l'utilisateur d'explorer l'impact d'une correction de montant sans créer un scénario entier. Modification purement frontend — aucun appel backend, aucune persistence.

**Files :**
- `frontend/src/components/forecast/PivotTable.tsx` (modifier)
- `frontend/src/content/documentation.ts` (modifier)

**Steps :**

- [ ] **Frontend — État overrides** : dans `PivotTable`, ajouter un état local :
  ```typescript
  const [overrides, setOverrides] = useState<Map<string, number>>(new Map());
  // clé = `${categoryId}:${month}`, valeur = montant overridé en centimes
  const hasOverrides = overrides.size > 0;
  ```

- [ ] **Frontend — Cellule éditable** : sur double-clic d'une cellule de prévision (mois futur uniquement, `month >= currentMonth`), afficher un `<input type="number" className="w-full bg-amber-50 border border-amber-300 rounded px-1 text-right font-mono text-[13px]" />` en place. Au `blur` ou `Enter`, enregistrer l'override. Montant saisi en euros, stocker en centimes (`Math.round(val * 100)`). La cellule overridée affiche le fond `bg-amber-50` et la valeur en `text-amber-900`.

- [ ] **Frontend — Recalcul des totaux** : la ligne "Total encaissements" et "Total décaissements" du pivot doit prendre en compte les overrides lors du rendu. Calculer `effectiveAmount(row, month) = overrides.get(key) ?? row.months[month]`. Recalculer les totaux de colonne avec les valeurs effectives.

- [ ] **Frontend — Bouton Réinitialiser** : afficher un bouton `<button onClick={() => setOverrides(new Map())} className="...">Réinitialiser les simulations</button>` dans le header de `PivotTable` uniquement si `hasOverrides`. Avec tooltip `title="Remet toutes les cellules à leurs valeurs réelles du scénario actif."`.

- [ ] **Frontend — Bandeau d'avertissement** : afficher un bandeau ambre en haut du tableau si `hasOverrides` : "Mode simulation actif — les valeurs modifiées (fond orange) sont locales à votre navigateur et ne sont pas enregistrées. Cliquez sur Réinitialiser pour revenir aux données réelles."

- [ ] **Documentation** : `FeatureDoc` `id: "what-if-simulation"`. "Ce que ça change quand tu cliques" = aucun changement en base, uniquement l'affichage local. "Ce que ça ne change pas" = le scénario, les forecast_lines, aucune donnée persistée.

---

## Task G9 — Saisonnalité par catégorie

**Pourquoi :** Comparaison "même mois N vs même mois N-1" par catégorie. Deviendra pleinement utile en 2027. Implémenter maintenant pour que les données s'accumulent. Gérer explicitement le cas données insuffisantes (4 mois en prod en mai 2026).

**Files :**
- `backend/app/services/analysis.py` (modifier — ajouter `compute_seasonality`)
- `backend/app/schemas/analysis.py` (modifier — ajouter schémas saisonnalité)
- `backend/app/api/analysis.py` (modifier — ajouter endpoint)
- `backend/tests/test_g9_seasonality.py` (créer)
- `frontend/src/api/seasonality.ts` (créer)
- `frontend/src/components/analyse/SeasonalityCard.tsx` (créer)
- `frontend/src/pages/AnalysePage.tsx` (modifier)
- `frontend/src/content/documentation.ts` (modifier)

**Steps :**

- [ ] **Backend — Schéma** : ajouter dans `backend/app/schemas/analysis.py` :
  ```python
  class SeasonalityPoint(BaseModel):
      month: str          # "YYYY-MM"
      year: int
      month_num: int      # 1-12
      amount_cents: int   # Σ transactions de la catégorie ce mois

  class SeasonalityResponse(BaseModel):
      entity_id: int
      category_id: int
      category_label: str
      months_available: int  # nombre de mois avec des données
      has_enough_data: bool  # True si >= 13 mois
      earliest_available: str | None  # "YYYY-MM"
      points: list[SeasonalityPoint]  # 24 mois max, triés chronologiquement
  ```

- [ ] **Backend — Service** : dans `backend/app/services/analysis.py`, ajouter `compute_seasonality(session, *, entity_id: int, category_id: int) -> SeasonalityResponse`. Logique : `SELECT DATE_TRUNC('month', operation_date) AS month, SUM(amount) FROM transactions WHERE bank_account_id IN (...) AND category_id = ? AND is_aggregation_parent = FALSE GROUP BY month ORDER BY month DESC LIMIT 24`. `has_enough_data = months_available >= 13`.

- [ ] **Backend — Endpoint** : dans `backend/app/api/analysis.py` :
  ```python
  @router.get("/seasonality", response_model=SeasonalityResponse)
  def get_seasonality(
      entity_id: int = Query(...),
      category_id: int = Query(...),
      user: User = Depends(get_current_user),
      session: Session = Depends(get_db),
  ) -> SeasonalityResponse:
      require_entity_access(session=session, user=user, entity_id=entity_id)
      return compute_seasonality(session, entity_id=entity_id, category_id=category_id)
  ```

- [ ] **Backend — Tests** : `backend/tests/test_g9_seasonality.py`. Cas : catégorie avec 4 mois → `has_enough_data=False`, `months_available=4`. Catégorie inconnue → `points=[]`.

- [ ] **Frontend — API** : créer `frontend/src/api/seasonality.ts` avec `fetchSeasonality` et `useSeasonality`.

- [ ] **Frontend — Composant** : créer `frontend/src/components/analyse/SeasonalityCard.tsx`. Header : `<select>` de catégories (utiliser `useCategories()` existant) pour choisir la catégorie analysée. Si `has_enough_data=false` : afficher le placeholder ambre : "Données insuffisantes pour afficher la saisonnalité ({months_available} mois disponibles sur 13 nécessaires). Ce graphique sera exploitable à partir de [dernier mois disponible + (13 - months_available) mois]." Si `has_enough_data=true` : `LineChart` Recharts avec 2 lignes (année N en bleu, année N-1 en gris), `XAxis` = mois abrégé (janv. à déc.), groupement par `month_num`. Tooltip "?" : `title="Compare les flux d'une catégorie mois par mois entre l'année en cours et l'année précédente pour détecter la saisonnalité."`.

- [ ] **Frontend — AnalysePage** : ajouter `<SeasonalityCard entityId={entityId ?? undefined} />` en bas de la grille (col-span-12), avant `EntitiesComparisonTable`.

- [ ] **Documentation** : `FeatureDoc` `id: "seasonality-chart"`. "Ce que ça ne change pas" = les transactions, catégories, aucune modification de données.

- [ ] **Run tests** : `docker exec horizon-backend-1 pytest tests/test_g9_seasonality.py -v` vert.

---

## Task G10 — Position de trésorerie nette par compte bancaire

**Pourquoi :** Granularité par compte. Agicap affiche le détail compte par compte avec variation. Dashboard actuel a un tableau texte — remplacer ou compléter avec des cartes visuelles incluant une sparkline.

**Files :**
- `backend/app/schemas/treasury.py` (modifier — ajouter `PerAccountBalance`, `PerAccountBalanceResponse`)
- `backend/app/api/treasury.py` (modifier — ajouter endpoint `/per-account`)
- `backend/tests/test_g10_per_account.py` (créer)
- `frontend/src/api/treasury.ts` (modifier — ajouter `fetchPerAccount`, `usePerAccount`)
- `frontend/src/components/treasury/PerAccountWidget.tsx` (créer)
- `frontend/src/pages/DashboardPage.tsx` (modifier)
- `frontend/src/content/documentation.ts` (modifier)

**Steps :**

- [ ] **Backend — Schéma** : ajouter dans `backend/app/schemas/treasury.py` :
  ```python
  class PerAccountBalance(BaseModel):
      account_id: int
      account_name: str
      bank_name: str
      iban_last4: str          # 4 derniers caractères de l'IBAN
      balance_cents: int       # solde courant (Σ closing_balance dernier import)
      balance_30d_ago_cents: int | None  # solde il y a 30 jours
      variation_30d_cents: int | None
      last_import_date: date | None
      sparkline: list[int]     # 30 points quotidiens en centimes (pour mini-chart)

  class PerAccountBalanceResponse(BaseModel):
      entity_id: int | None
      accounts: list[PerAccountBalance]
  ```

- [ ] **Backend — Endpoint** : ajouter dans `backend/app/api/treasury.py` l'endpoint `GET /api/treasury/per-account`. Logique par compte :
  - Solde courant : `closing_balance` du dernier `ImportRecord COMPLETED` avec `period_end` non nul.
  - Solde 30 jours avant : dernier `ImportRecord COMPLETED` dont `period_end <= today - 30`.
  - Sparkline : reconstruire 30 points quotidiens via `_compute_balance_trend` pour chaque compte individuellement. Retourner les balances en centimes (`int(balance * 100)`).
  - Si l'entité est `None` : retourner tous les comptes accessibles à l'utilisateur.

- [ ] **Backend — Tests** : `backend/tests/test_g10_per_account.py`. Vérifier : 1 compte → 1 `PerAccountBalance`, sparkline de longueur 30, accès interdit si entité étrangère.

- [ ] **Frontend — API** : ajouter `fetchPerAccount` et `usePerAccount` dans `frontend/src/api/treasury.ts`.

- [ ] **Frontend — Composant** : créer `frontend/src/components/treasury/PerAccountWidget.tsx`. Grille responsive de cartes. Chaque carte :
  - Nom du compte + banque en en-tête + `...IBAN_last4`.
  - Solde courant en grand (`text-[22px] font-mono font-semibold`), coloré selon positif/négatif.
  - Variation 30j : badge `↑ +X € (+Y%)` vert ou `↓ −X € (−Y%)` rouge.
  - Mini sparkline : `<AreaChart width={120} height={40} data={sparkline.map((v, i) => ({ v }))}><Area dataKey="v" ... /></AreaChart>` sans axes ni tooltip.
  - Date du dernier import sous forme "dernier import : JJ/MM/AAAA".
  - Tooltip "?" sur le titre de la section : `title="Solde par compte bancaire reconstruit à partir du dernier relevé importé, avec variation sur 30 jours."`.

- [ ] **Frontend — DashboardPage** : remplacer ou augmenter le tableau "Soldes par compte" existant avec `<PerAccountWidget entityId={entityId} />`. Placer après les KPI cards, avant les graphiques de répartition.

- [ ] **Documentation** : `FeatureDoc` `id: "per-account-balance"`.

- [ ] **Run tests** : `docker exec horizon-backend-1 pytest tests/test_g10_per_account.py -v` vert.

---

## Task G11 — Export CSV/XLSX généralisé

**Pourquoi :** Toute analyse produite par Horizon doit pouvoir sortir dans un tableur. Indispensable pour les clôtures mensuelles, les reporting banquiers, les audits comptables.

**Files :**
- `backend/app/api/transactions.py` (modifier)
- `backend/app/api/admin_audit.py` (modifier)
- `backend/app/api/analysis.py` (modifier)
- `backend/app/api/forecast_pivot.py` (modifier)
- `backend/tests/test_g11_exports.py` (créer)
- `frontend/src/api/exports.ts` (créer)
- `frontend/src/pages/AnalysePage.tsx` (modifier)
- `frontend/src/pages/AdminAuditLogPage.tsx` (modifier)
- `frontend/src/pages/TransactionsPage.tsx` (modifier)
- `frontend/src/pages/ForecastV2Page.tsx` (modifier)
- `frontend/src/content/documentation.ts` (modifier)

**Steps :**

- [ ] **Vérification openpyxl** : `docker exec horizon-backend-1 pip show openpyxl 2>&1`. Si présent → implémenter CSV + XLSX. Si absent → CSV uniquement. Note le résultat ici avant de coder.

- [ ] **Backend — Helper export** : créer dans `backend/app/api/` un module `_export_helpers.py` (préfixe underscore = interne, non exposé comme router) avec :
  ```python
  import csv, io
  from fastapi.responses import StreamingResponse

  def csv_response(headers: list[str], rows: list[list], filename: str) -> StreamingResponse:
      buf = io.StringIO()
      w = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)
      w.writerow(headers)
      w.writerows(rows)
      buf.seek(0)
      return StreamingResponse(
          iter([buf.getvalue().encode("utf-8-sig")]),  # BOM pour Excel FR
          media_type="text/csv",
          headers={"Content-Disposition": f'attachment; filename="{filename}"'},
      )

  # Si openpyxl présent :
  def xlsx_response(headers: list[str], rows: list[list], filename: str) -> StreamingResponse:
      from openpyxl import Workbook
      wb = Workbook()
      ws = wb.active
      ws.append(headers)
      for r in rows:
          ws.append(r)
      buf = io.BytesIO()
      wb.save(buf)
      buf.seek(0)
      return StreamingResponse(
          iter([buf.getvalue()]),
          media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          headers={"Content-Disposition": f'attachment; filename="{filename}"'},
      )
  ```

- [ ] **Backend — Endpoints export** : ajouter dans chaque router un endpoint `GET .../export`:
  - `GET /api/transactions/export?entity_id=X&from=...&to=...&format=csv` dans `transactions.py`. Colonnes : Date, Libellé, Tiers, Catégorie, Montant (€), Compte. Réutilise les mêmes filtres que `list_transactions`.
  - `GET /api/admin/audit/export?format=csv` dans `admin_audit.py`. Colonnes : Date/heure, Utilisateur, Action, Entité, Détails. Admin only.
  - `GET /api/analysis/drift/export?entity_id=X&format=csv` dans `analysis.py`. Colonnes : Catégorie, M-1 (€), Moyenne M-2/M-4 (€), Écart (€), Écart %. Réutilise `compute_category_drift`.
  - `GET /api/analysis/top-movers/export?entity_id=X&format=csv` dans `analysis.py`.
  - `GET /api/analysis/yoy/export?entity_id=X&format=csv` dans `analysis.py`.
  - `GET /api/forecast/pivot/export?entity_id=X&scenario_id=Y&from=...&to=...&format=csv` dans `forecast_pivot.py`. Matrice catégorie × mois.
  - Paramètre `format: Literal["csv", "xlsx"] = "csv"`. Si `format="xlsx"` mais openpyxl absent → 400 `{"detail": "Format XLSX non disponible sur ce serveur."}`.

- [ ] **Backend — Tests** : `backend/tests/test_g11_exports.py`. Vérifier `Content-Disposition`, `Content-Type`, BOM UTF-8-sig, nombre de lignes (headers + N data rows). Tester le 400 si XLSX demandé sans openpyxl (mocker l'import).

- [ ] **Frontend — API exports** : créer `frontend/src/api/exports.ts` :
  ```typescript
  export async function downloadExport(url: string, filename: string): Promise<void> {
    const resp = await apiFetch<Blob>(url, { responseType: "blob" });
    const href = URL.createObjectURL(resp);
    const a = document.createElement("a");
    a.href = href; a.download = filename;
    a.click();
    URL.revokeObjectURL(href);
  }
  ```
  Note : `apiFetch` devra accepter `responseType: "blob"` — adapter `client.ts` si nécessaire (ajouter le cas `blob` dans le switch de parsing).

- [ ] **Frontend — Boutons export** : sur chaque page éligible, ajouter un bouton "Exporter CSV" (dropdown "CSV / XLSX" si openpyxl confirmé) :
  - `TransactionsPage` : bouton dans le header à côté du filtre période.
  - `AnalysePage` : bouton dans chaque carte (Drift, TopMovers, YoY) via une petite icône de téléchargement `⬇` en haut à droite de la carte.
  - `AdminAuditLogPage` : bouton dans l'en-tête.
  - `ForecastV2Page` : bouton "Exporter le pivot" dans l'en-tête de `PivotTable`.
  - Tooltip "?" sur chaque bouton : `title="Télécharge les données affichées au format CSV (séparateur point-virgule, encodage UTF-8 avec BOM pour Excel)."`.

- [ ] **Documentation** : `FeatureDoc` `id: "export-csv"`. "Ce que ça ne change pas" = aucune donnée modifiée, export en lecture seule.

- [ ] **Run tests** : `docker exec horizon-backend-1 pytest tests/test_g11_exports.py -v` vert.

---

## Task G12 — Snooze/acquittement de dérive

**Pourquoi :** Sans acquittement, les alertes de dérive s'accumulent et perdent leur valeur. Un "snooze 30 jours" permet de signaler "je sais, c'est normal ce mois-ci" et de retrouver un tableau propre. Avec un log d'acquittement qui permet l'auditabilité.

**Files :**
- `backend/alembic/versions/20260507_g1200_drift_acks.py` (créer)
- `backend/app/models/drift_ack.py` (créer)
- `backend/app/models/__init__.py` (modifier)
- `backend/app/schemas/drift_ack.py` (créer)
- `backend/app/api/drift_acks.py` (créer)
- `backend/app/api/router.py` (modifier)
- `backend/app/services/analysis.py` (modifier — `compute_category_drift` lit `DriftAck`)
- `backend/tests/test_g12_drift_acks.py` (créer)
- `frontend/src/api/driftAcks.ts` (créer)
- `frontend/src/components/analyse/CategoryDriftTable.tsx` (modifier)
- `frontend/src/content/documentation.ts` (modifier)

**Steps :**

- [ ] **Backend — Migration** : créer `backend/alembic/versions/20260507_g1200_drift_acks.py`. Révision `h0r1z0ng1200`, down_revision = dernière migration en prod.
  ```python
  def upgrade() -> None:
      op.create_table(
          "drift_acks",
          sa.Column("id", sa.Integer(), primary_key=True),
          sa.Column("entity_id", sa.Integer(), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
          sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id", ondelete="CASCADE"), nullable=False),
          sa.Column("snoozed_until", sa.Date(), nullable=False),
          sa.Column("acknowledged_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
          sa.Column("acknowledged_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
          sa.Column("note", sa.String(500), nullable=True),
      )
      op.create_index("ix_drift_acks_entity_category", "drift_acks", ["entity_id", "category_id"])
      op.create_index("ix_drift_acks_snoozed_until", "drift_acks", ["snoozed_until"])
  ```

- [ ] **Backend — Modèle** : créer `backend/app/models/drift_ack.py` :
  ```python
  from sqlalchemy.orm import Mapped, mapped_column
  from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, func
  from app.models.base import Base
  from datetime import date, datetime
  from typing import Optional

  class DriftAck(Base):
      __tablename__ = "drift_acks"
      id: Mapped[int] = mapped_column(primary_key=True)
      entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True)
      category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
      snoozed_until: Mapped[date] = mapped_column(Date, nullable=False)
      acknowledged_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
      acknowledged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
      note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
  ```

- [ ] **Backend — models/__init__.py** : ajouter `from app.models.drift_ack import DriftAck`.

- [ ] **Backend — Schéma** : créer `backend/app/schemas/drift_ack.py` :
  ```python
  from pydantic import BaseModel
  from datetime import date, datetime

  class DriftSnoozeRequest(BaseModel):
      entity_id: int
      category_id: int
      snooze_days: int = 30
      note: str | None = None

  class DriftAckRead(BaseModel):
      id: int
      entity_id: int
      category_id: int
      snoozed_until: date
      acknowledged_at: datetime
      acknowledged_by_id: int | None
      note: str | None
  ```

- [ ] **Backend — Endpoint** : créer `backend/app/api/drift_acks.py` :
  ```python
  router = APIRouter(prefix="/api/analysis/drift-acks", tags=["analysis"])

  @router.post("/", response_model=DriftAckRead, status_code=201)
  def snooze_drift(
      body: DriftSnoozeRequest,
      user: User = Depends(get_current_user),
      session: Session = Depends(get_db),
  ) -> DriftAckRead:
      require_entity_access(session=session, user=user, entity_id=body.entity_id)
      ack = DriftAck(
          entity_id=body.entity_id,
          category_id=body.category_id,
          snoozed_until=date.today() + timedelta(days=body.snooze_days),
          acknowledged_by_id=user.id,
          note=body.note,
      )
      session.add(ack)
      session.commit()
      session.refresh(ack)
      return DriftAckRead.model_validate(ack)

  @router.get("/", response_model=list[DriftAckRead])
  def list_drift_acks(
      entity_id: int = Query(...),
      user: User = Depends(get_current_user),
      session: Session = Depends(get_db),
  ) -> list[DriftAckRead]:
      require_entity_access(session=session, user=user, entity_id=entity_id)
      today = date.today()
      acks = session.scalars(
          select(DriftAck)
          .where(DriftAck.entity_id == entity_id, DriftAck.snoozed_until >= today)
          .order_by(DriftAck.acknowledged_at.desc())
      ).all()
      return [DriftAckRead.model_validate(a) for a in acks]
  ```

- [ ] **Backend — compute_category_drift** : dans `backend/app/services/analysis.py`, modifier `compute_category_drift` pour exclure les catégories snoozées. Ajouter en début de fonction :
  ```python
  from datetime import date
  from app.models.drift_ack import DriftAck

  today = date.today()
  snoozed_category_ids: set[int] = set(
      session.scalars(
          select(DriftAck.category_id)
          .where(
              DriftAck.entity_id == entity_id,
              DriftAck.snoozed_until >= today,
          )
      ).all()
  )
  ```
  Puis dans la construction de `CategoryDriftRow`, remplacer `status="alert"` par `status="snoozed"` si `row.category_id in snoozed_category_ids` (ne pas filtrer totalement — afficher avec statut distinct pour transparence). Ajouter `"snoozed"` dans le `Literal` du schéma `CategoryDriftRow.status`.

- [ ] **Backend — Router** : ajouter `from app.api import drift_acks` et `api_router.include_router(drift_acks.router)` dans `router.py`.

- [ ] **Backend — Tests** : `backend/tests/test_g12_drift_acks.py`. Vérifier : POST snooze → 201, GET liste → ack présent, `snoozed_until` = today + 30. Vérifier que `compute_category_drift` retourne `status="snoozed"` pour une catégorie acquittée.

- [ ] **Frontend — API** : créer `frontend/src/api/driftAcks.ts` avec `postDriftAck`, `fetchDriftAcks`, `useDriftAcks`, hook de mutation `useSnoozeDrift` via `useMutation` de react-query.

- [ ] **Frontend — CategoryDriftTable** : ajouter une colonne "Action" dans le tableau. Pour les lignes `status="alert"` : bouton `Snooze 30 j` (`bg-amber-50 text-amber-900 border border-amber-200 text-[12px] px-2 py-1 rounded`). Au clic : `confirm("Mettre en veille cette dérive pour 30 jours ?")` → si OK, appeler `useSnoozeDrift.mutate(...)` → invalider la query `category-drift` via `queryClient.invalidateQueries`. Pour les lignes `status="snoozed"` : badge "En veille" gris + date `snoozed_until`. Tooltip "?" sur l'en-tête de la colonne : `title="Snooze 30 jours : masque temporairement l'alerte sans supprimer la donnée. Elle réapparaîtra après expiration."`.

- [ ] **Documentation** : `FeatureDoc` `id: "drift-snooze"`. "Ce que ça change quand tu cliques" = crée un enregistrement en base `drift_acks` avec expiration J+30, supprime l'alerte rouge du tableau pendant 30 jours. "Ce que ça ne change pas" = les transactions, catégories, le calcul de dérive (toujours calculé, juste affiché différemment). "Quand l'utiliser" = dépense exceptionnelle connue (achat de matériel, prime de fin d'année, sinistre) qui ne doit pas déclencher d'alerte pendant le mois suivant.

- [ ] **Migration** : `docker exec horizon-backend-1 alembic upgrade head`.

- [ ] **Run tests** : `docker exec horizon-backend-1 pytest tests/test_g12_drift_acks.py -v` vert.

---

## Séquence de build recommandée

```
Phase 1 — Backend fondations (bloquant pour le reste)
  G12-migration → G1-endpoint → G10-endpoint → G4-service → G2-endpoint → G9-endpoint → G11-helpers

Phase 2 — Tests backend complets
  pytest tests/test_g1* tests/test_g2* tests/test_g4* tests/test_g9* tests/test_g10* tests/test_g11* tests/test_g12* -v

Phase 3 — Frontend read-only (pas de mutation)
  G1-DailyBalanceChart → G10-PerAccountWidget → G3-WorkingCapitalBanner → G9-SeasonalityCard → G4-AnomalyCard → G2-Rolling13WChart

Phase 4 — Frontend avec mutation/interaction
  G8-PivotTable overrides → G7-ScenarioOverlay → G12-CategoryDriftTable snooze → G11-boutons export

Phase 5 — Documentation et tests frontend
  documentation.ts (toutes les FeatureDoc) → npx tsc -b → npx vitest --run

Phase 6 — Vérifications finales
  docker exec horizon-backend-1 pytest tests/ -v
  cd frontend && npx tsc -b && npx vitest --run
```

---

## Fichiers de tests à créer

| Fichier | Task | Points de couverture |
|---|---|---|
| `backend/tests/test_g1_daily_balance.py` | G1 | 0 import → `[]`, 90 points triés, accès refusé |
| `backend/tests/test_g2_rolling13w.py` | G2 | 13 points, `is_past` correct, `week_label` ISO |
| `backend/tests/test_g4_anomalies.py` | G4 | p95 calculé, ratio correct, < 5 transactions ignorées |
| `backend/tests/test_g9_seasonality.py` | G9 | `has_enough_data=False` avec 4 mois |
| `backend/tests/test_g10_per_account.py` | G10 | sparkline 30 pts, variation_30d calculée |
| `backend/tests/test_g11_exports.py` | G11 | BOM, séparateur `;`, Content-Disposition, 400 si XLSX absent |
| `backend/tests/test_g12_drift_acks.py` | G12 | POST 201, GET filtre actifs, drift revient `snoozed` |

---

