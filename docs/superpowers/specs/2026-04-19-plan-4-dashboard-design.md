# Plan 4 — Tableau de bord (design)

- **Date** : 2026-04-19
- **Statut** : v1 — design
- **Base** : spec produit de référence `2026-04-16-clone-agicap-design.md` §3 (Tableau de bord)

---

## 1. Objectif

Remplacer le placeholder `DashboardPage` par un tableau de bord fonctionnel
affichant l'activité financière réelle des entités accessibles à l'utilisateur :

- 4 indicateurs clés (KPIs)
- 1 graphique temporel entrées/sorties par jour
- 1 filtre de période (30 jours / ce mois / mois précédent / 90 jours)
- 1 filtre d'entité (si l'utilisateur a accès à ≥ 2 entités)

**Hors périmètre** (reporté à une v2 ou au Plan 5 Prévisionnel) :
- Répartition par catégorie (pie / donut)
- Comparaison M-1 / M-12
- Export CSV
- Multi-devises
- Graphique cumulatif soldes consolidés

---

## 2. Architecture

### 2.1. Backend — nouvel endpoint

Un seul endpoint agrège tout ce dont l'UI a besoin :

```
GET /api/dashboard/summary
    ?period=current_month|previous_month|last_30d|last_90d
    [&entity_id=<int>]
```

**Réponse** :

```json
{
  "period_label": "Avril 2026",
  "period_start": "2026-04-01",
  "period_end": "2026-04-30",
  "total_balance": "12345.67",          // Σ des derniers soldes connus
  "total_balance_asof": "2026-04-18",   // date du statement le + récent
  "inflows": "25430.00",                // Σ crédits sur la période
  "outflows": "-18220.15",              // Σ débits sur la période (négatif)
  "uncategorized_count": 12,            // tx categorized_by=NONE sur la période
  "daily": [
    {"date": "2026-04-01", "inflows": "0.00", "outflows": "-120.50"},
    ...
  ]
}
```

**Règles métier** :
- Filtrage par `UserEntityAccess` systématique (pas de fuite trans-entités).
- `total_balance` = somme des `closing_balance` du dernier `ImportRecord`
  de chaque `BankAccount` accessible. Si pas d'import → 0.
- Transactions agrégées `is_aggregation_parent=True` **exclues** des sommes
  (c'est le comportement standard du codebase, cf. Plan 1).
- Transactions sans `bank_account` accessible exclues.
- `entity_id` optionnel : si fourni et accessible, restreint aux comptes de
  cette entité ; sinon, toutes entités accessibles.
- Si `entity_id` fourni mais inaccessible → `403`.

**Période** :
- `current_month` : du 1er du mois courant à aujourd'hui
- `previous_month` : du 1er au dernier jour du mois précédent
- `last_30d` : `[today-29, today]`
- `last_90d` : `[today-89, today]`

### 2.2. Frontend — réécriture `DashboardPage`

**Composants** :
- `DashboardPage` (page) — orchestration, gère l'état `period` + `entityId`
- `PeriodSelector` (inline segmented control, 4 options)
- `EntityFilter` (select, caché si user a 1 seule entité accessible)
- `KpiCard` (réutilisable, affiche label/value/hint, support montant signé)
- `CashflowChart` (bar chart empilé : barres vertes = entrées, rouges = sorties, axe X = jours)

**Bibliothèque de graphiques** : `recharts`
- Maintenue activement, déjà dépendance fréquente de shadcn projects
- API déclarative compatible React 18
- Poids bundle acceptable (~90 kB gzipped) pour 1 chart

**Data flow** :
- `useQuery(['dashboard-summary', period, entityId])` → appelle `/api/dashboard/summary`
- Cache 60s, refetch à la navigation
- Loading skeleton sur chacune des 4 cards
- Empty state si toutes les valeurs sont 0 + aucun import

### 2.3. Modèles / DB

**Aucun changement de schéma.** Les agrégats sont calculés à la volée
par SQL sur les tables existantes (`transactions`, `import_records`,
`bank_accounts`, `user_entity_access`).

Si perf devient un problème (seuil : > 500 ms sur la summary), on ajoutera
des index dédiés ou une vue matérialisée — non nécessaire au lancement.

---

## 3. Décomposition en phases

| Phase | Contenu | Fichiers principaux |
|---|---|---|
| **A — Backend summary** | Endpoint `/api/dashboard/summary`, schéma pydantic, tests unitaires + permissions | `app/api/dashboard.py`, `app/schemas/dashboard.py`, `tests/test_api_dashboard.py` |
| **B — Frontend deps + wiring** | Installer `recharts`, typer `DashboardSummary`, hook `useDashboardSummary`, `KpiCard` component | `frontend/package.json`, `src/types/api.ts`, `src/api/dashboard.ts`, `src/components/KpiCard.tsx` |
| **C — Frontend page** | Réécriture `DashboardPage` : filtres + 4 KPIs + `CashflowChart` | `src/pages/DashboardPage.tsx`, `src/components/dashboard/*.tsx` |
| **D — Tests front + déploiement** | Vitest sur page + composants, rebuild prod, smoke test | `src/pages/__tests__/DashboardPage.test.tsx` |

---

## 4. Critères d'acceptation

- [ ] `GET /api/dashboard/summary?period=current_month` retourne un JSON valide pour un user admin avec accès à ≥ 1 entité
- [ ] Un user READER voit les mêmes valeurs (permissions identiques sur la lecture)
- [ ] Un user sans accès à l'entité demandée reçoit 403
- [ ] Les montants agrégés excluent les parents SEPA (`is_aggregation_parent=True`)
- [ ] Le DashboardPage affiche 4 KPI cards avec les valeurs de l'API
- [ ] Le graphique entrées/sorties affiche 1 barre par jour de la période
- [ ] Le changement de période re-fetch les données (visible dans Network)
- [ ] Couverture tests backend ≥ 85% sur le nouveau module
- [ ] Couverture tests frontend ≥ 70% sur DashboardPage
- [ ] Déployé en prod, accessible sur `https://horizon.acreedconsulting.com/`
- [ ] Aucune régression sur les pages existantes (npm run build OK, suite pytest verte)

---

## 5. Risques / compromis

- **Risque perf** : requête SQL quotidienne sur plusieurs milliers de tx.
  Mitigation : un seul `GROUP BY date` sur un index `(bank_account_id, operation_date)` déjà présent, pas de N+1 côté ORM.
- **Compromis bundle** : `recharts` ajoute ~90 kB gzipped. Alternative (viser < 30 kB) = lib custom SVG basée sur `<svg><rect/></svg>`, mais complexité de maintenance > bénéfice pour un MVP.
- **Décision différée** : pie chart par catégorie — à voir après retour d'usage. Pour l'instant, la valeur "Non catégorisées" suffit à guider le user vers les actions correctives.

---

## 6. Prochaine étape

Écrire le plan d'implémentation `2026-04-19-plan-4-dashboard.md` puis exécution via sous-agents.
