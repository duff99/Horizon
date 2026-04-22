# Plan 5b — Forecast v2 Agicap-like : Design Spec

**Date :** 2026-04-22
**Auteur :** Tristan + Claude (brainstorming skill)
**Status :** Approuvé — scope "big bang" avec Engagements inclus.

## Objectif

Porter le module Prévisionnel d'Horizon au niveau d'Agicap : tableau pivot catégories × mois, 3 modes Payées/Engagées/Prévisionnel, méthodes de calcul configurables par catégorie, scénarios multiples, vue consolidée comptes, et nouveau module Engagements pour les factures reçues/émises non encore payées.

## Scope (big bang)

**Inclus :**
- Nouveau module **Engagements** : CRUD factures fournisseur / client, matching auto ou manuel avec les transactions
- **Scénarios** multiples par entité (1 défaut + N custom)
- **ForecastLine** : règle de calcul par (scenario, catégorie, entité)
- 8 méthodes de calcul : `RECURRING_FIXED`, `AVG_3M`, `AVG_6M`, `AVG_12M`, `PREVIOUS_MONTH`, `SAME_MONTH_LAST_YEAR`, `BASED_ON_CATEGORY`, `FORMULA`
- **Formules DSL v1** simples : `{Catégorie_M-N} op valeur op {...}` avec `+ - * /`
- **Page Prévisionnel v2** : pivot hiérarchique catégories × 15 mois glissants + barres hautes réalisé/prévi + courbe solde + drawer de cellule 3 onglets
- **Vue consolidée comptes** : popover avec checkbox par compte bancaire
- **Widget dashboard** "Réalisé mois en cours vs mois précédent"
- L'existant `forecast_entry` reste (pour coups exceptionnels ; combiné avec `forecast_line`)

**Exclus (reportés) :**
- Import OCR des factures
- Connexion email pour récupération auto des factures
- Rapprochement inter-compagnies
- Export PDF

## Architecture

### Approche : Hybride (règles stockées + calcul à la volée + cache HTTP court)

Les règles (`forecast_line`) sont stockées en DB. Le calcul du pivot s'exécute à la requête (pas de recalcul asynchrone complexe à invalider). Un `Cache-Control: max-age=30, stale-while-revalidate=60` protège l'UX sur les ré-hovers.

### Modèles de données (nouveaux)

**`commitment`** (Engagements)
```
id                  int PK
entity_id           int FK entities
counterparty_id     int FK counterparties (nullable)
category_id         int FK categories (nullable — force la catégorisation mais tolère inconnu)
bank_account_id     int FK bank_accounts (nullable — compte prévu)
direction           enum('in', 'out')
amount_cents        int (positif, signe donné par direction)
issue_date          date (date d'émission/réception de la facture)
expected_date       date (date de paiement prévue)
status              enum('pending', 'paid', 'cancelled')
matched_transaction_id int FK transactions (nullable)
reference           text (n° facture, bon de commande, etc.)
description         text
pdf_attachment_id   int FK imports.id (nullable — réutilise le stockage PDF)
created_by_id       int FK users
created_at, updated_at
```

**`forecast_scenario`**
```
id            int PK
entity_id     int FK entities
name          text
description   text nullable
is_default    bool  (exactly 1 true per entity — enforced via partial unique index)
created_by_id int FK users
created_at, updated_at
```

**`forecast_line`** (règle de calcul par cellule agrégée)
```
id                int PK
scenario_id       int FK forecast_scenarios
entity_id         int FK entities (dénormalisé pour accélérer la query, = scenario.entity_id)
category_id       int FK categories
method            enum('RECURRING_FIXED', 'AVG_3M', 'AVG_6M', 'AVG_12M',
                       'PREVIOUS_MONTH', 'SAME_MONTH_LAST_YEAR',
                       'BASED_ON_CATEGORY', 'FORMULA')
amount_cents      int nullable  (pour RECURRING_FIXED)
base_category_id  int FK categories nullable (pour BASED_ON_CATEGORY)
ratio             numeric(5,4) nullable (ex 0.2000 = 20 %, pour BASED_ON_CATEGORY)
formula_expr      text nullable (pour FORMULA)
start_month       date nullable (1er du mois, inclus) — si null = toujours
end_month         date nullable (1er du mois, inclus) — si null = toujours
updated_by_id     int FK users
created_at, updated_at

UNIQUE (scenario_id, category_id)  — une seule règle par (scenario, catégorie)
```

### Moteur de calcul (`backend/app/services/forecast_engine.py`)

Pour chaque cellule `(scenario_id, entity_id, category_id, month)` :

```
def compute_cell(scenario_id, entity_id, category_id, month) -> CellValue:
    realized = sum(transactions matching (entity, category, month))
    committed = sum(commitments matching (entity, category, month) with status=pending)

    if month < current_month:
        forecast = 0  # passé → pas de forecast
    else:
        line = get_forecast_line(scenario_id, category_id)  # optional
        forecast_line_value = evaluate_line(line, month) if line else 0
        manual_entries = sum(forecast_entries matching (entity, category, month))
        forecast = forecast_line_value + manual_entries

    return CellValue(realized, committed, forecast,
                     total=max(realized, realized + committed, forecast))
```

Convention pour le **mois courant** : `total = realized + committed + forecast_restant` (où `forecast_restant = max(0, forecast - realized - committed)`).

### Méthodes de calcul

| method | paramètres | formule |
|---|---|---|
| `RECURRING_FIXED` | `amount_cents` | constant |
| `AVG_3M` | — | moyenne des 3 mois précédents (transactions + commitments payés) |
| `AVG_6M` | — | moyenne 6 mois |
| `AVG_12M` | — | moyenne 12 mois |
| `PREVIOUS_MONTH` | — | réalisé du mois précédent |
| `SAME_MONTH_LAST_YEAR` | — | réalisé du même mois l'année précédente |
| `BASED_ON_CATEGORY` | `base_category_id`, `ratio` | réalisé/prévi de la catégorie base × ratio |
| `FORMULA` | `formula_expr` | parser DSL → évaluation |

### DSL Formule (v1)

**Grammaire simplifiée (tokens + precedence classique)** :
```
expr     := term (('+' | '-') term)*
term     := factor (('*' | '/') factor)*
factor   := NUMBER | REF | '(' expr ')' | '-' factor
REF      := '{' IDENT ('_M-' DIGIT+)? '}'
IDENT    := [A-Za-z0-9_ÀÉÈÊ][A-Za-z0-9_ÀÉÈÊ ]*  (nom de catégorie, trim + case-insensitive)
```

**Exemples valides** :
- `{Ventes} * 0.20` (TVA collectée)
- `{Ventes_M-1} * 1.03` (indexation)
- `{Salaires} + 500` (bonus)
- `({Ventes} + {Prestations}) / 2`

**Résolution `{IDENT}`** : cherche une catégorie dont `name` matche (insensitive, trim). `_M-N` = N mois avant le mois en cours de calcul. Si la catégorie n'existe pas → HTTPException 422 à la création de la ligne.

**Protections** :
- Parser maison récursif descendant (pas d'`eval`)
- Prévention des cycles : détecter si la formule référence (directement ou transitivement) sa propre catégorie → 422
- Timeout d'évaluation 500ms par cellule

### Matching Engagements ↔ Transactions

**À l'import** (dans `services/imports.py`) :
- Pour chaque nouvelle transaction, cherche les commitments `pending` de la même `entity_id`, `direction`, `amount_cents ±1€`, `expected_date ±7j`
- Si 1 match unique → lien auto, commitment passe en `paid`, `matched_transaction_id = tx.id`
- Si 0 ou >1 → rien (action manuelle)

**Manuel** :
- Page Engagements : pour chaque commitment pending, bouton "Lier à une transaction" → modale avec suggestions (fuzzy match) + recherche libre

### Endpoints API

```
# Engagements
GET    /api/commitments?entity_id&status&from&to&direction&page&per_page
POST   /api/commitments
GET    /api/commitments/{id}
PATCH  /api/commitments/{id}
DELETE /api/commitments/{id}
POST   /api/commitments/{id}/match   body: {transaction_id}
POST   /api/commitments/{id}/unmatch
GET    /api/commitments/{id}/suggest-matches  → top 10 tx candidates
POST   /api/commitments/{id}/attachment  upload PDF
GET    /api/commitments/{id}/attachment  download PDF

# Scenarios
GET    /api/forecast/scenarios?entity_id
POST   /api/forecast/scenarios   body: {entity_id, name, description, is_default}
PATCH  /api/forecast/scenarios/{id}
DELETE /api/forecast/scenarios/{id}  # 409 si is_default=true et seul

# Lines
GET    /api/forecast/lines?scenario_id
PUT    /api/forecast/lines  body: {scenario_id, category_id, method, ...params}  (upsert)
DELETE /api/forecast/lines/{id}
POST   /api/forecast/lines/validate-formula  body: {scenario_id, formula_expr} → 200|422

# Pivot (endpoint principal)
GET    /api/forecast/pivot
       ?scenario_id=…&entity_id=…
       &from=2026-01&to=2027-03
       &accounts=1,4,7   # IDs de bank_account ; omis = tous
→ {
    months: ["2026-01", ..., "2027-03"],
    opening_balance_cents: 2150000,
    closing_balance_projection_cents: [...],   # une valeur par mois
    rows: [
      {
        category_id, parent_id, label, level,  # hiérarchie
        direction: "in"|"out",
        cells: [
          { month, realized_cents, committed_cents, forecast_cents, total_cents, line_method?, line_params? }
        ],
        monthly_totals: {...}
      }
    ],
    realized_series: [...],    # pour les barres hautes
    forecast_series: [...]
  }

# Dashboard comparaison
GET    /api/dashboard/month-comparison?entity_id
→ { current: {in, out, month_label}, previous: {in, out, month_label} }
```

### Frontend — pages

**Page `/engagements`** (nouvelle) — CRUD avec table filtrable (entity, status, période, direction), modale de création, bouton Matcher avec drawer de suggestions.

**Page `/previsionnel` v2** (remplace l'existante)
- Layout vertical :
  1. Header : titre + `<EntitySelector />` + `<ScenarioSelector />` + `<ConsolidatedAccountsPopover />` + boutons (Nouveau scénario, Exporter, Rafraîchir)
  2. Barres hautes (recharts ComposedChart) : barres empilées encaissements/décaissements par mois + courbe solde fin de mois superposée
  3. Tableau pivot scrollable horizontalement : colonne figée gauche "Catégorie" + colonnes mois scrollables
- Hiérarchie du tableau (exemple vu chez Agicap) :
  ```
  Trésorerie en début de mois                    [valeurs cell par mois]
  [+] Encaissements (total)
      [+] Flux opérationnels
          Encaissements clients
          Factor
          ...
      [+] Flux d'investissement
      [+] Flux de financement
      À Catégoriser
  [+] Décaissements (total)
      [+] Flux opérationnels
      ...
      TVA
  Variation nette de cash
  Trésorerie en fin de mois
  ```
- Cellules :
  - Mois passé : réalisé en noir
  - Mois courant : mix réalisé + engagées + prévi, avec barre verticale bleue en dessous
  - Mois futur : prévi en italique gris
- Clic sur cellule future → drawer latéral `CellEditorDrawer` avec 3 onglets :
  - **Payées** : liste des transactions de ce (mois, catégorie, entité, comptes filtrés)
  - **Engagées** : liste des commitments
  - **Prévisionnel** : formulaire radio méthode + sous-options + preview live + bouton "Enregistrer"

**Widget dashboard** "Comparaison mois" : 2 barres côte à côte (mois courant vs mois précédent, encaissements + décaissements). Intégré dans `DashboardPage.tsx` sous les KPIs.

### Sidebar

Ajout d'un item "Engagements" dans le groupe Pilotage, entre "Transactions" et "Prévisionnel".

### Design (skills frontend utilisées)

Application de `gpt-taste` + `design-taste-frontend` :
- Tokens existants respectés (`bg-panel`, `shadow-card`, `border-line-soft`, `text-ink`, `text-ink-2`, `text-muted-foreground`, `bg-accent`, couleurs cream/dark du design B)
- Pivot : pas de card-box autour ; lignes `border-b border-line-soft` entre catégories ; hover ligne `bg-panel-2/50`
- Cellules numériques en `font-mono tabular-nums` pour alignement
- Motion : transitions `duration-150 ease-out` sur hover / drawer open (pas de bounce excessif)
- Drawer : largeur 420px, overlay semi-opaque, close sur ESC/clic extérieur/bouton
- Couleurs sémantiques : réalisé neutre (`text-ink`), prévi (`text-ink-2 italic`), positif (`text-emerald-700`), négatif (`text-rose-700`)

## Tests attendus

- **Backend** : tests unitaires moteur (chaque méthode de calcul), tests intégration endpoints (CRUD + pivot + matching), tests DSL parser (valide, invalide, cycle), +60 tests au total visés
- **Frontend** : tests composants pivot (rendering + navigation), drawer (changement onglet), snapshot du shape API côté hooks

## Découpage en phases pour l'implémentation

1. **Engagements backend** : modèle + migration + endpoints + matching dans imports
2. **Engagements frontend** : page CRUD + modale match + lien sidebar
3. **Scenarios + lines backend** : modèles + migration + endpoints CRUD + seed scénario "Principal" par défaut
4. **Forecast engine** : moteur de calcul + DSL parser + tests unitaires exhaustifs
5. **Pivot endpoint** : agrégation SQL + sérialisation
6. **Forecast v2 frontend** : pivot + barres + drawer cellule + scenario selector + consolidated accounts popover
7. **Dashboard comparison widget** : endpoint + composant React
8. **E2E + merge + deploy** : tests bout-en-bout, merge sur main, tag `plan-5b-done`, rebuild prod

## Risques & mitigations

- **Perf pivot sur 15 mois × 50 catégories** : requête SQL unique avec GROUP BY month, category → <200ms même sur 10k transactions. Index sur `transactions(bank_account_id, operation_date, category_id)` et `commitments(entity_id, expected_date, status, category_id)`.
- **Cohérence formule + changement nom catégorie** : si un user renomme une catégorie référencée par `{Old_name}`, la formule casse → message d'erreur explicite à l'évaluation (pas de crash), tooltip d'avertissement côté UI.
- **Scénario default supprimé** : impossible via UI (contrainte DB `is_default` + endpoint qui refuse `DELETE` sur is_default=true si seul).

## Non-objectifs

- Pas de machine learning / détection auto de méthode
- Pas de collaboration multi-user en temps réel (Horizon reste mono-admin)
- Pas de versioning d'historique des règles
